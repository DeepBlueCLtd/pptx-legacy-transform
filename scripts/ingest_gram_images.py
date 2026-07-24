"""Prep-time transform: import author-supplied gram images and relink GLCs.

Many grams ship with only a ``.wav`` asset, rendered live by the on-PC GLC
viewer. Students only ever inspect the spectrogram visually, so the author
opens each ``.wav`` in the analysis tool, screenshots the displayed gram, and
saves it -- in a *parallel incoming tree* -- named for the duration shown on
the y-axis plus the wav's own stem. The duration is separated from the stem by
either a space or an underscore (the author uses both, sometimes after the
minutes, sometimes after the seconds)::

    5m26s WAV 1.jpg          # 5 min 26 s of "WAV 1"
    21m WAVE 3.png           # 21 min of "WAVE 3"
    10m_0 - 600 Hz.jpg       # 10 min of "0 - 600 Hz" (underscore separator)
    7m20s_0 - 441 Hz.jpg     # 7 min 20 s of "0 - 441 Hz"

Matching is **case-insensitive** at both the folder and the stem level: the
hand-typed incoming names drift in case from ``source\\`` (an incoming
``7m_WAV 1.jpg`` matches a source ``Wav 1.wav``), so case is never a reason to
report a mismatch. The copied image takes the *wav's* own casing, keeping each
gram folder internally consistent. Genuine drift (missing spaces, changed
tokens) is still reported for the operator to fix.

The incoming tree mirrors ``source\\`` but **omits the per-document container
folder**: ``incoming\\<doc>\\<gram>\\<image>`` maps to
``source\\<doc>\\<container>\\<gram>\\`` where ``<container>`` is the *single*
sub-folder of the source document folder (identified by uniqueness, never by
name).

This runs in two phases:

* **verify** (default, read-only) -- match incoming doc/gram folders and image
  stems against the source corpus and write a mismatch report
  (``ingest_report.txt``) grouped by outcome class, with nearest-candidate
  suggestions and a survey of unparseable duration tokens. The operator fixes
  the **incoming** tree by hand and re-runs until clean. Nothing on disk is
  changed except the report and the log.
* **apply** (``--apply``) -- for every verified match, copy the image beside its
  ``.glc`` renamed to the wav's stem, rewrite the ``.glc``'s ``<filename>`` to
  point at it, and insert ``<bitmap_crop_values><bottom_crop>N</bottom_crop>``
  ``</bitmap_crop_values>`` (the duration in whole seconds) so the extractor
  reads it as the gram's ``time_end`` and the generator embeds the image inline.

**Demon images (issue #151).** The same incoming folders may also carry
*demon* images -- an alternately-rendered gram view carrying a ``Demon`` token,
either leading (``Demon - 10m2s 0-40Hz.png``, ``Demon - 0-40Hz.png``) or after a
leading duration token (``4m10s_Demon - 0 - 40 Hz.jpg``). These
are **additive**, not ``.wav`` replacements, so they skip the duration/stem
matching entirely. In verify they are listed in a ``DEMON IMAGES`` report
section; in apply each is copied into the source gram folder under its original
name and gets a ``demon.glc`` marker cloned from the folder's first hyperlinked
``.glc`` -- with its ``<filename>`` repointed at the image and its band settings
overwritten to the fixed 0 - 40 Hz range. The marker is the signal ``extract``
keys on to emit a leading demon GramFrame; the demon's time period is the
image's pixel height (issue #148), so no ``bottom_crop`` is written.

**Deliberate divergence from ``relink_glc_to_image.py``:** that sibling prep
tool moves the superseded ``.wav`` aside to ``<name>.wav.bak``. This tool
**leaves the ``.wav`` untouched, in place** -- a future user may want the audio
and cannot be assumed able to rename file suffixes, and the generator only
copies what the ``.glc`` references, so the wav never reaches ``dita\\``.
Idempotency is carried instead by the "GLC already references an image" skip:
once a gram is converted it is never reconsidered, so re-runs are safe.

Logging follows the dual-output convention: stdout + ``ingest.log`` in the cwd.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# Sibling-import the canonical GLC parser and the relink helpers (mirrors
# relink_glc_to_image.py) so this script reads and rewrites a .glc exactly as
# the rest of the pipeline does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_to_csv import parse_glc  # noqa: E402
from relink_glc_to_image import FILENAME_TAG_RE, setup_logging  # noqa: E402

LOGGER = logging.getLogger(__name__)

# Image extensions an author screenshot may carry (spec: jpg/jpeg/png only --
# narrower than relink's set, which also allows .gif). Case-insensitive test.
IMAGE_EXTENSIONS: Tuple[str, ...] = (".jpg", ".jpeg", ".png")

# Extensions the generator treats as an inline spectrogram image (used to
# recognise an already-converted GLC). Mirrors the generator's dispatch set.
GLC_IMAGE_EXTENSIONS: Tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif")

# A duration token: whole minutes, optionally minutes-plus-seconds. Case
# tolerated ("10M"). Nothing else parses -- other shapes feed the
# unparseable-duration survey. Anchored: the whole leading token must match.
DURATION_RE = re.compile(r"^(?P<m>\d+)m(?:(?P<s>\d{1,2})s)?$", re.IGNORECASE)

# A "demon" image is an alternately-rendered gram view identified by a ``Demon``
# token (issue #151). The token is either at the very start
# (``Demon - 10m2s 0-40Hz.png``, ``Demon - 0-40Hz.png``) or after a leading
# duration token and a space/underscore separator
# (``4m10s_Demon - 0 - 40 Hz.jpg``). It is *additive* -- never a .wav
# replacement -- so a matching file is intercepted before the duration/stem
# matching path and handled apart. Anchored so ``WAV 1``-style screenshots (no
# ``Demon`` token) never match.
DEMON_PREFIX_RE = re.compile(
    r"^(?:\d+m(?:\d{1,2}s)?[ _])?demon\b", re.IGNORECASE)

# The demon GramFrame's frequency range is always 0 - 40 Hz (issue #151). The
# generator derives the band from ``bandwidth``/``bandcentre`` the way it does
# for every gram (band spans bandwidth/2 either side of bandcentre), so a 0..40
# range is a width of 40 centred on 20. These are baked into the demon.glc so
# extract/generate read them through the ordinary band path (confirmed design:
# ingest owns the constant, not extract or the generator).
DEMON_BANDWIDTH = "40"
DEMON_BANDCENTRE = "20"

# Targeted band-element rewrites for the demon.glc (byte-preserving text edits,
# not an XML round-trip -- consistent with build_relinked_glc_text). Each must
# match exactly once in the cloned template; a template missing either element
# cannot encode the fixed band and is skipped (fail-loud on our own output).
BANDWIDTH_TAG_RE = re.compile(r"(<bandwidth>)(.*?)(</bandwidth>)", re.DOTALL)
BANDCENTRE_TAG_RE = re.compile(r"(<bandcentre>)(.*?)(</bandcentre>)", re.DOTALL)

# The duration token is separated from the stem by a space or an underscore
# ("11m Wav 1", "10m_0 - 600 Hz", "7m20s_0 - 441 Hz"). Split on the first.
DURATION_SEPARATOR_RE = re.compile(r"[ _]")

# A source document folder normally holds exactly one sub-folder -- the
# "<doc> Files" container that holds the gram folders. One publication instead
# lays its gram folders *directly* under the doc folder, with no container
# tier. A doc folder with this many or more sub-folders is read as that flat
# layout (its sub-folders are the grams) rather than reported as ambiguous;
# the normal single-container case has exactly one, so the two never collide.
FLAT_DOC_MIN_GRAMS = 8


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------

@dataclass
class CandidateImage:
    """An incoming author screenshot, parsed into duration + stem."""

    path: Path
    raw_token: str
    seconds: Optional[int]  # None -> duration token did not parse
    stem: str               # remainder after the token; "" -> unparseable
    extension: str          # as delivered, case preserved

    @property
    def parseable(self) -> bool:
        return self.seconds is not None and bool(self.stem)


@dataclass
class GlcRef:
    """One ``.glc`` in a gram folder and the asset it currently references."""

    glc_path: Path
    referenced_basename: str
    has_crop: bool


@dataclass
class GramFolderView:
    """The GLC-referenced assets of a source gram folder, keyed by asset stem."""

    folder: Path
    wav_refs: Dict[str, List[GlcRef]] = field(default_factory=dict)
    image_refs: Dict[str, List[GlcRef]] = field(default_factory=dict)
    unreadable: List[Path] = field(default_factory=list)


@dataclass
class Outcome:
    """A single finding the report and tally aggregate."""

    kind: str
    key: str                     # display path (sorted within its section)
    note: str = ""               # formatted detail for the report
    drift: Optional[Tuple[str, Optional[str], Optional[str]]] = None


# Outcome kinds -- the taxonomy shared by the report sections and the tally.
KIND_MATCHED = "matched"
KIND_UNMATCHED_DOC = "unmatched-doc"
KIND_AMBIGUOUS_DOC = "structurally-ambiguous-doc"
KIND_UNMATCHED_GRAM = "unmatched-gram"
KIND_UNPARSEABLE = "unparseable-duration"
KIND_UNMATCHED_IMAGE = "unmatched-image"
KIND_AMBIGUOUS = "ambiguous"
KIND_ALREADY = "already-converted"
KIND_GLC_UNREADABLE = "glc-unreadable"
KIND_GLC_CROPPED = "glc-already-cropped"
KIND_DEMON = "demon-image"

# Report section order + human headings.
SECTION_ORDER: Tuple[Tuple[str, str], ...] = (
    (KIND_UNMATCHED_DOC, "UNMATCHED DOCUMENTS"),
    (KIND_AMBIGUOUS_DOC, "STRUCTURALLY AMBIGUOUS DOCUMENTS"),
    (KIND_UNMATCHED_GRAM, "UNMATCHED GRAM FOLDERS"),
    (KIND_UNPARSEABLE, "UNPARSEABLE DURATIONS"),
    (KIND_UNMATCHED_IMAGE, "UNMATCHED IMAGES"),
    (KIND_AMBIGUOUS, "AMBIGUOUS"),
    (KIND_GLC_UNREADABLE, "UNREADABLE GLCS"),
    (KIND_GLC_CROPPED, "ALREADY-CROPPED GLCS"),
    (KIND_ALREADY, "ALREADY CONVERTED"),
    (KIND_DEMON, "DEMON IMAGES"),
    (KIND_MATCHED, "MATCHED"),
)


@dataclass
class Tally:
    """Per-kind counts plus apply-mode work counters."""

    counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    images_copied: int = 0
    glcs_rewritten: int = 0
    demon_markers: int = 0

    def bump(self, kind: str) -> None:
        self.counts[kind] += 1


# -----------------------------------------------------------------------------
# Parsing
# -----------------------------------------------------------------------------

def parse_image_filename(path: Path) -> Optional[CandidateImage]:
    """Parse an incoming file into a CandidateImage, or None if not an image.

    Splits the stem on the first whitespace run: the leading token is matched
    against the duration grammar, the remainder is the stem used to find the
    wav. A file whose extension is not an accepted image type returns None (the
    caller debug-logs and ignores it). An image whose token does not parse, or
    which has no stem after the token, is returned with ``parseable`` False.
    """
    ext = path.suffix
    if ext.lower() not in IMAGE_EXTENSIONS:
        return None

    full_stem = path.stem  # filename without the final extension
    parts = DURATION_SEPARATOR_RE.split(full_stem, maxsplit=1)
    raw_token = parts[0]
    remainder = parts[1].strip() if len(parts) > 1 else ""

    match = DURATION_RE.match(raw_token)
    seconds: Optional[int] = None
    if match:
        minutes = int(match.group("m"))
        secs = int(match.group("s")) if match.group("s") else 0
        seconds = minutes * 60 + secs

    return CandidateImage(
        path=path,
        raw_token=raw_token,
        seconds=seconds,
        stem=remainder,
        extension=ext,
    )


def build_gram_folder_view(folder: Path) -> GramFolderView:
    """Parse every ``.glc`` in ``folder`` into a stem-keyed view of its assets.

    A GLC whose inner filename is a ``.wav`` lands in ``wav_refs``; an image
    inner filename lands in ``image_refs`` (used to recognise an already-
    converted gram). A GLC that yields no inner filename (malformed or missing)
    is recorded in ``unreadable`` and excluded from matching. ``has_crop`` flags
    a GLC that already carries a ``<bitmap_crop_values>`` structure.

    The bucket keys are the referenced asset stems **casefolded**, so an
    incoming screenshot matches its wav regardless of case drift; each ref
    keeps the wav's original-case basename for naming the copied image.
    """
    view = GramFolderView(folder=folder)
    for glc_path in sorted(folder.glob("*.glc")):
        if not glc_path.is_file():
            continue
        doc = parse_glc(glc_path)
        basename = doc.image_filename
        if not basename:
            view.unreadable.append(glc_path)
            continue
        try:
            raw = glc_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            raw = ""
        has_crop = "<bitmap_crop_values" in raw
        ref = GlcRef(glc_path=glc_path, referenced_basename=basename,
                     has_crop=has_crop)
        stem_key = Path(basename).stem.casefold()
        suffix = Path(basename).suffix.lower()
        if suffix == ".wav":
            view.wav_refs.setdefault(stem_key, []).append(ref)
        elif suffix in GLC_IMAGE_EXTENSIONS:
            view.image_refs.setdefault(stem_key, []).append(ref)
        # Any other extension is anomalous (per glc-schema): not a wav, not one
        # of our images -- it cannot match an incoming screenshot, so it is
        # simply not indexed.
    return view


# -----------------------------------------------------------------------------
# Suggestions and drift labelling
# -----------------------------------------------------------------------------

def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def drift_label(
    name: str, candidate: Optional[str]
) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    """Classify how ``name`` drifts from its nearest ``candidate``.

    Probes in order (each mismatch lands in exactly one class): case-only,
    whitespace-only, case+whitespace, single-token drift (returns the differing
    token pair for trend aggregation), else ``other``. Returns None when there
    is no candidate or the two are identical.
    """
    if not candidate or name == candidate:
        return None
    if name.casefold() == candidate.casefold():
        return ("case-only", None, None)
    if _collapse(name) == _collapse(candidate):
        return ("whitespace-only", None, None)
    if _collapse(name).casefold() == _collapse(candidate).casefold():
        return ("case+whitespace", None, None)
    name_tokens = name.split()
    cand_tokens = candidate.split()
    if len(name_tokens) == len(cand_tokens):
        diffs = [(a, b) for a, b in zip(name_tokens, cand_tokens) if a != b]
        if len(diffs) == 1:
            return ("token-drift", diffs[0][0], diffs[0][1])
    return ("other", None, None)


def _nearest(name: str, candidates: Sequence[str]) -> Optional[str]:
    hits = get_close_matches(name, list(candidates), n=1, cutoff=0.6)
    return hits[0] if hits else None


def _suggestion_note(
    name: str, candidates: Sequence[str]
) -> Tuple[str, Optional[Tuple[str, Optional[str], Optional[str]]]]:
    """Return a report note listing up to 3 nearest candidates + a drift label."""
    close = get_close_matches(name, list(candidates), n=3, cutoff=0.6)
    if not close:
        return ("no close candidate", None)
    drift = drift_label(name, close[0])
    label = _format_drift(drift)
    quoted = ", ".join('"%s"' % c for c in close)
    suffix = " [%s]" % label if label else ""
    return ("nearest: %s%s" % (quoted, suffix), drift)


def _format_drift(
    drift: Optional[Tuple[str, Optional[str], Optional[str]]]
) -> str:
    if drift is None:
        return ""
    label, a, b = drift
    if label == "token-drift":
        return "token-drift('%s' -> '%s')" % (a, b)
    return label


# -----------------------------------------------------------------------------
# GLC mutation (apply)
# -----------------------------------------------------------------------------

def _indent_unit(text: str, filename_indent: str) -> str:
    """Infer one indentation step from the file, defaulting to two spaces."""
    match = re.search(r"^(\s*)<data_source>", text, re.MULTILINE)
    if match:
        parent = match.group(1)
        if filename_indent.startswith(parent) and len(filename_indent) > len(parent):
            return filename_indent[len(parent):]
    return "  "


def build_relinked_glc_text(text: str, new_basename: str, seconds: int) -> str:
    """Return ``text`` with the first ``<filename>`` repointed + a crop block.

    A targeted text edit (not an XML round-trip) so every other byte is
    preserved: the first ``<filename>`` inner text is replaced with
    ``new_basename`` and a ``<bitmap_crop_values>`` block carrying
    ``<bottom_crop>{seconds}</bottom_crop>`` is inserted immediately after the
    corresponding ``</filename>``, indented to match the file. Raises
    ``ValueError`` if the ``<filename>`` anchor is absent, so a malformed file
    is never half-written.
    """
    new_text, count = FILENAME_TAG_RE.subn(
        lambda m: m.group(1) + new_basename + m.group(3), text, count=1)
    if count != 1:
        raise ValueError("no <filename> element to rewrite")

    close_idx = new_text.index("</filename>")
    after = close_idx + len("</filename>")

    # Indentation of the <filename> line drives the crop block's alignment.
    line_start = new_text.rfind("\n", 0, close_idx) + 1
    line_indent_match = re.match(r"\s*", new_text[line_start:])
    indent = line_indent_match.group(0) if line_indent_match else "  "
    unit = _indent_unit(new_text, indent)

    block = (
        "\n%s<bitmap_crop_values>"
        "\n%s%s<bottom_crop>%d</bottom_crop>"
        "\n%s</bitmap_crop_values>"
        % (indent, indent, unit, seconds, indent)
    )
    return new_text[:after] + block + new_text[after:]


def build_demon_glc_text(text: str, new_basename: str) -> str:
    """Return ``text`` (a cloned template GLC) turned into a demon marker.

    Two targeted, byte-preserving text edits (issue #151): the first
    ``<filename>`` inner text is repointed at ``new_basename`` (the demon
    image), and the ``<bandwidth>``/``<bandcentre>`` inner text is overwritten to
    encode the fixed 0 - 40 Hz range (``DEMON_BANDWIDTH`` / ``DEMON_BANDCENTRE``)
    so extract and the generator read it through the ordinary band path with no
    demon special-case. No ``bottom_crop`` is inserted: the demon's time period
    is the image's pixel height, measured at extraction (issue #148).

    Raises ``ValueError`` when any of the three anchors (``<filename>``,
    ``<bandwidth>``, ``<bandcentre>``) is absent, so a template that cannot
    encode the fixed band is never written half-formed -- the caller skips it
    with a warning rather than emit a broken marker.
    """
    new_text, count = FILENAME_TAG_RE.subn(
        lambda m: m.group(1) + new_basename + m.group(3), text, count=1)
    if count != 1:
        raise ValueError("no <filename> element to rewrite")

    new_text, bw = BANDWIDTH_TAG_RE.subn(
        lambda m: m.group(1) + DEMON_BANDWIDTH + m.group(3), new_text, count=1)
    if bw != 1:
        raise ValueError("no <bandwidth> element to rewrite")

    new_text, bc = BANDCENTRE_TAG_RE.subn(
        lambda m: m.group(1) + DEMON_BANDCENTRE + m.group(3), new_text, count=1)
    if bc != 1:
        raise ValueError("no <bandcentre> element to rewrite")

    return new_text


def _demon_marker_name(index: int) -> str:
    """Deterministic demon-marker filename for the *index*-th demon (1-based).

    The issue names the marker ``demon.glc`` (singular); when a gram folder
    carries several demon images the markers extend as ``demon-2.glc``,
    ``demon-3.glc``, … in incoming-filename order so each references its own
    image and extract emits them in a stable order ahead of the Lofars.
    """
    return "demon.glc" if index == 1 else "demon-%d.glc" % index


def _first_template_glc(source_gram: Path) -> Optional[Path]:
    """Return the gram folder's first hyperlinked ``.glc`` to clone, or None.

    "First hyperlinked glc for that folder" (issue #151): the first ``.glc`` in
    sorted order, excluding any ``demon*.glc`` marker (so a re-run never clones a
    previously-created demon marker). Returns None when the folder has no
    template ``.glc`` -- the demon cannot be wired up and is skipped.
    """
    for glc_path in sorted(source_gram.glob("*.glc")):
        if glc_path.is_file() and not glc_path.name.lower().startswith("demon"):
            return glc_path
    return None


# -----------------------------------------------------------------------------
# Matching / classification -- shared by verify and apply
# -----------------------------------------------------------------------------

def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def process_gram(
    incoming_gram: Path, source_gram: Path, incoming_root: Path,
    source_root: Path, *, apply: bool, outcomes: List[Outcome], tally: Tally,
) -> None:
    """Match a matched incoming/source gram folder pair; apply if requested."""
    view = build_gram_folder_view(source_gram)

    for glc_path in view.unreadable:
        outcomes.append(Outcome(
            KIND_GLC_UNREADABLE, _rel(glc_path, source_root),
            note="no inner filename (malformed or missing)"))
        tally.bump(KIND_GLC_UNREADABLE)

    # Collect and parse the incoming images. Demon images (leading "Demon"
    # token) are intercepted here -- they are additive, not .wav replacements,
    # so they never enter the duration/stem matching path (issue #151).
    images: List[CandidateImage] = []
    demon_images: List[Path] = []
    for entry in sorted(incoming_gram.iterdir()):
        if not entry.is_file():
            continue
        if (entry.suffix.lower() in IMAGE_EXTENSIONS
                and DEMON_PREFIX_RE.match(entry.stem)):
            demon_images.append(entry)
            continue
        candidate = parse_image_filename(entry)
        if candidate is None:
            LOGGER.debug("ignore non-image file: %s", entry)
            continue
        images.append(candidate)

    # Group parseable images by casefolded stem so case drift collapses onto
    # one key (and two case-variant screenshots collide as ambiguous).
    parseable: Dict[str, List[CandidateImage]] = defaultdict(list)
    for candidate in images:
        if not candidate.parseable:
            outcomes.append(Outcome(
                KIND_UNPARSEABLE, _rel(candidate.path, incoming_root),
                note='token "%s"' % candidate.raw_token))
            tally.bump(KIND_UNPARSEABLE)
        else:
            parseable[candidate.stem.casefold()].append(candidate)

    available_wavs = ", ".join(sorted(
        Path(ref.referenced_basename).stem
        for refs in view.wav_refs.values() for ref in refs)) or "(none)"

    for key in sorted(parseable):
        group = parseable[key]
        display_stem = group[0].stem
        if key in view.wav_refs:
            if len(group) > 1:
                claimants = ", ".join(sorted(c.path.name for c in group))
                outcomes.append(Outcome(
                    KIND_AMBIGUOUS, _rel(incoming_gram, incoming_root),
                    note='wav "%s" claimed by %s; none applied'
                         % (display_stem, claimants)))
                tally.bump(KIND_AMBIGUOUS)
                continue
            candidate = group[0]
            outcomes.append(Outcome(
                KIND_MATCHED, _rel(candidate.path, incoming_root),
                note='wav "%s"' % display_stem))
            tally.bump(KIND_MATCHED)
            if apply:
                _apply_match(candidate, view.wav_refs[key], source_gram,
                             outcomes, tally)
        elif key in view.image_refs:
            for candidate in group:
                outcomes.append(Outcome(
                    KIND_ALREADY, _rel(candidate.path, incoming_root),
                    note='stem "%s" already an image in the GLC'
                         % candidate.stem))
                tally.bump(KIND_ALREADY)
        else:
            for candidate in group:
                outcomes.append(Outcome(
                    KIND_UNMATCHED_IMAGE, _rel(candidate.path, incoming_root),
                    note='stem "%s"; folder wavs: %s'
                         % (candidate.stem, available_wavs)))
                tally.bump(KIND_UNMATCHED_IMAGE)

    if demon_images:
        _process_demon_images(
            demon_images, source_gram, incoming_root, source_root,
            apply=apply, outcomes=outcomes, tally=tally)


def _process_demon_images(
    demon_images: List[Path], source_gram: Path, incoming_root: Path,
    source_root: Path, *, apply: bool, outcomes: List[Outcome], tally: Tally,
) -> None:
    """Report (verify) or seed (apply) a demon marker for each demon image.

    Each demon image is copied into ``source_gram`` **keeping its original
    filename** and gets a ``demon.glc`` marker cloned from the folder's first
    hyperlinked ``.glc``, repointed at the image with the fixed 0 - 40 Hz band
    baked in (issue #151). Markers are named ``demon.glc``, ``demon-2.glc``, …
    in incoming-filename order. Verify mode only reports; apply performs the
    copy + marker write. Idempotent: a marker that already exists is left as-is
    and reported "already present".
    """
    template = _first_template_glc(source_gram)
    for index, image in enumerate(sorted(demon_images, key=lambda p: p.name),
                                  start=1):
        marker_name = _demon_marker_name(index)
        marker_path = source_gram / marker_name
        rel_image = _rel(image, incoming_root)

        if not apply:
            outcomes.append(Outcome(
                KIND_DEMON, rel_image,
                note='demon image (would seed %s)' % marker_name))
            tally.bump(KIND_DEMON)
            continue

        if marker_path.exists():
            outcomes.append(Outcome(
                KIND_DEMON, rel_image,
                note='already present: %s' % marker_name))
            tally.bump(KIND_DEMON)
            continue

        if template is None:
            LOGGER.warning(
                "skip demon (no template .glc in %s): %s", source_gram, image)
            outcomes.append(Outcome(
                KIND_DEMON, rel_image,
                note='no hyperlinked .glc to clone; skipped'))
            tally.bump(KIND_DEMON)
            continue

        try:
            text = template.read_text(encoding="utf-8")
            marker_text = build_demon_glc_text(text, image.name)
        except (OSError, ValueError) as exc:
            LOGGER.warning("skip demon (could not build marker): %s [%s]",
                           image, exc)
            outcomes.append(Outcome(
                KIND_DEMON, rel_image,
                note='could not build marker: %s' % exc))
            tally.bump(KIND_DEMON)
            continue

        # Copy the demon image beside the marker (original name preserved) and
        # write the marker. Order: image first, so a marker never references a
        # missing image even if the run is interrupted between the two writes.
        shutil.copyfile(image, source_gram / image.name)
        tally.images_copied += 1
        marker_path.write_text(marker_text, encoding="utf-8")
        tally.demon_markers += 1
        LOGGER.info("demon: %s -> %s (marker %s, band 0-40 Hz)",
                    image, source_gram / image.name, marker_name)
        outcomes.append(Outcome(
            KIND_DEMON, rel_image, note='seeded %s' % marker_name))
        tally.bump(KIND_DEMON)


def _apply_match(
    candidate: CandidateImage, refs: Sequence[GlcRef], source_gram: Path,
    outcomes: List[Outcome], tally: Tally,
) -> None:
    """Copy the image and repoint every wav-backed GLC that shares its stem."""
    writable = [r for r in refs if not r.has_crop]
    cropped = [r for r in refs if r.has_crop]

    for ref in sorted(cropped, key=lambda r: r.glc_path.name):
        outcomes.append(Outcome(
            KIND_GLC_CROPPED, ref.glc_path.name,
            note="already carries bitmap_crop_values; skipped"))
        tally.bump(KIND_GLC_CROPPED)

    if not writable:
        # Nothing to rewrite; do not orphan an image copy in the folder.
        return

    # Name the copy after the wav's own stem (its casing), not the incoming
    # screenshot's -- the hand-typed name may differ in case (incoming
    # "WAV 1" vs source "Wav 1.wav"), and the copy should sit consistently
    # beside the wav it replaces.
    wav_stem = Path(sorted(writable, key=lambda r: r.glc_path.name)[0]
                    .referenced_basename).stem
    target_name = wav_stem + candidate.extension
    destination = source_gram / target_name
    shutil.copyfile(candidate.path, destination)
    tally.images_copied += 1
    LOGGER.info("copied %s -> %s", candidate.path, destination)

    assert candidate.seconds is not None  # parseable guaranteed by caller
    for ref in sorted(writable, key=lambda r: r.glc_path.name):
        try:
            text = ref.glc_path.read_text(encoding="utf-8")
            new_text = build_relinked_glc_text(text, target_name,
                                               candidate.seconds)
        except (OSError, ValueError) as exc:
            LOGGER.warning("skip GLC (could not rewrite): %s [%s]",
                           ref.glc_path, exc)
            outcomes.append(Outcome(
                KIND_GLC_UNREADABLE, ref.glc_path.name,
                note="could not rewrite: %s" % exc))
            tally.bump(KIND_GLC_UNREADABLE)
            continue
        ref.glc_path.write_text(new_text, encoding="utf-8")
        tally.glcs_rewritten += 1
        LOGGER.info("relinked %s: %s -> %s (bottom_crop=%d)",
                    ref.glc_path, ref.referenced_basename, target_name,
                    candidate.seconds)


# -----------------------------------------------------------------------------
# Tree walk
# -----------------------------------------------------------------------------

def _subdirs(path: Path) -> List[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir())


def ingest_tree(
    incoming_root: Path, source_root: Path, *, apply: bool,
) -> Tuple[List[Outcome], Tally]:
    """Walk the incoming tree, match against source, and (if apply) convert."""
    outcomes: List[Outcome] = []
    tally = Tally()

    source_docs = _subdirs(source_root)
    source_doc_names = [p.name for p in source_docs]
    # Case-insensitive folder match: key by casefolded name, suggest and report
    # against the real names.
    source_doc_map = {p.name.casefold(): p for p in source_docs}

    for incoming_doc in _subdirs(incoming_root):
        source_doc = source_doc_map.get(incoming_doc.name.casefold())
        if source_doc is None:
            note, drift = _suggestion_note(incoming_doc.name, source_doc_names)
            outcomes.append(Outcome(
                KIND_UNMATCHED_DOC, incoming_doc.name, note=note, drift=drift))
            tally.bump(KIND_UNMATCHED_DOC)
            continue

        subdirs = _subdirs(source_doc)
        if len(subdirs) == 1:
            # Normal layout: the single "<doc> Files" container holds the grams.
            container = subdirs[0]
        elif len(subdirs) >= FLAT_DOC_MIN_GRAMS:
            # Flat layout (observed in one publication): the gram folders sit
            # directly under the doc folder, with no container tier.
            container = source_doc
        else:
            outcomes.append(Outcome(
                KIND_AMBIGUOUS_DOC, _rel(source_doc, source_root),
                note="%d subdirectories (expected exactly 1 container, or >= %d "
                     "gram folders for a flat publication); skipped"
                     % (len(subdirs), FLAT_DOC_MIN_GRAMS)))
            tally.bump(KIND_AMBIGUOUS_DOC)
            continue
        container_grams = _subdirs(container)
        container_gram_names = [p.name for p in container_grams]
        container_gram_map = {p.name.casefold(): p for p in container_grams}

        for incoming_gram in _subdirs(incoming_doc):
            source_gram = container_gram_map.get(incoming_gram.name.casefold())
            if source_gram is None:
                note, drift = _suggestion_note(
                    incoming_gram.name, container_gram_names)
                outcomes.append(Outcome(
                    KIND_UNMATCHED_GRAM,
                    _rel(incoming_gram, incoming_root), note=note, drift=drift))
                tally.bump(KIND_UNMATCHED_GRAM)
                continue
            process_gram(incoming_gram, source_gram, incoming_root,
                         source_root, apply=apply, outcomes=outcomes,
                         tally=tally)

    return outcomes, tally


# -----------------------------------------------------------------------------
# Report
# -----------------------------------------------------------------------------

def _summary_line(tally: Tally, *, apply: bool) -> str:
    verb = "applied" if apply else "matched"
    parts = ["%s %d" % (verb, tally.counts.get(KIND_MATCHED, 0))]
    for kind, _heading in SECTION_ORDER:
        if kind == KIND_MATCHED:
            continue
        parts.append("%s %d" % (kind, tally.counts.get(kind, 0)))
    if apply:
        parts.append("glcs_rewritten %d" % tally.glcs_rewritten)
        parts.append("images_copied %d" % tally.images_copied)
        parts.append("demon_markers %d" % tally.demon_markers)
    return ", ".join(parts)


def render_report(
    outcomes: Sequence[Outcome], tally: Tally, *, incoming_root: Path,
    source_root: Path, apply: bool,
) -> str:
    """Render the deterministic plain-text report (no timestamps in the body)."""
    lines: List[str] = ["INGEST REPORT",
                        "incoming: %s" % incoming_root,
                        "source:   %s" % source_root,
                        "mode:     %s" % ("apply" if apply else "verify"),
                        ""]

    by_kind: Dict[str, List[Outcome]] = defaultdict(list)
    for outcome in outcomes:
        by_kind[outcome.kind].append(outcome)

    for kind, heading in SECTION_ORDER:
        entries = by_kind.get(kind)
        if not entries:
            continue
        lines.append("== %s (%d) ==" % (heading, len(entries)))
        for outcome in sorted(entries, key=lambda o: o.key):
            if outcome.note:
                lines.append("%s  ->  %s" % (outcome.key, outcome.note))
            else:
                lines.append(outcome.key)
        lines.append("")

    trends = _aggregate_trends(outcomes)
    if trends:
        lines.append("== TRENDS ==")
        lines.extend(trends)
        lines.append("")

    lines.append("== SUMMARY ==")
    lines.append(_summary_line(tally, apply=apply))
    lines.append("")
    return "\n".join(lines)


def _aggregate_trends(outcomes: Sequence[Outcome]) -> List[str]:
    """Aggregate drift labels across mismatches so systematic drifts surface."""
    token_pairs: Dict[Tuple[str, str], int] = defaultdict(int)
    simple: Dict[str, int] = defaultdict(int)
    for outcome in outcomes:
        if outcome.drift is None:
            continue
        label, a, b = outcome.drift
        if label == "token-drift" and a is not None and b is not None:
            token_pairs[(a, b)] += 1
        else:
            simple[label] += 1

    lines: List[str] = []
    for (a, b), count in sorted(token_pairs.items()):
        lines.append("token-drift '%s' -> '%s' x %d" % (a, b, count))
    for label, count in sorted(simple.items()):
        lines.append("%s x %d" % (label, count))
    return lines


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    setup_logging(Path("ingest.log"))
    parser = argparse.ArgumentParser(
        description="Import author gram images and relink wav-backed GLCs "
                    "(prep-time). Default is a read-only verify/report run; "
                    "pass --apply to perform the conversion.")
    parser.add_argument("--incoming-root", required=True, type=Path,
                        dest="incoming_root",
                        help="author delivery tree (read-only in every mode)")
    parser.add_argument("--source-root", required=True, type=Path,
                        dest="source_root",
                        help="source corpus root (mutated only with --apply)")
    parser.add_argument("--apply", action="store_true", dest="apply",
                        help="convert verified matches (default: verify only)")
    args = parser.parse_args(argv)

    incoming_root: Path = args.incoming_root
    source_root: Path = args.source_root
    for label, root in (("incoming-root", incoming_root),
                        ("source-root", source_root)):
        if not root.exists():
            LOGGER.error("%s does not exist: %s", label, root)
            return 1
        if not root.is_dir():
            LOGGER.error("%s is not a directory: %s", label, root)
            return 1

    mode = "apply" if args.apply else "verify"
    LOGGER.info("ingesting gram images (%s): incoming=%s source=%s",
                mode, incoming_root, source_root)

    outcomes, tally = ingest_tree(incoming_root, source_root, apply=args.apply)

    report = render_report(outcomes, tally, incoming_root=incoming_root,
                           source_root=source_root, apply=args.apply)
    report_path = Path("ingest_report.txt")
    report_path.write_text(report, encoding="utf-8")

    LOGGER.info("done (%s): %s", mode, _summary_line(tally, apply=args.apply))
    LOGGER.info("report written to %s", report_path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    rc = main()
    # Preserve CLI exit codes when invoked as a script, but stay silent when
    # invoked from an interactive REPL via runpy.run_path -- sys.exit would
    # otherwise kill the interpreter. sys.ps1 is only defined interactively.
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)

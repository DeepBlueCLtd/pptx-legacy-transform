# Phase 0 Research: PPTX to DITA Migration Pipeline

**Feature**: PPTX to DITA Migration Pipeline
**Date**: 2026-05-08

This document records the decisions taken to resolve the open questions left
by the source specification, plus best-practice choices for each technology
the project depends on. The pipeline is constrained by an unusual operating
context (air-gapped, no AI, no `pip install` after handover), so several
decisions trade convenience for long-term debuggability.

---

## R1. Shape grouping — deferred behind a documented stub

**Decision**: Ship `extract_grams_from_slide()` in `extract_to_csv.py` as a
stub that raises `NotImplementedError` with a docstring listing the five
questions that the introspection report must answer (PNG hyperlink type,
link-box positioning, shape naming consistency, spatial proximity
viability, GROUP shapes). All surrounding infrastructure is fully
implemented around the stub.

**Rationale**: The source spec mandates this directly (FR-015, section 5.3
of the spec document). The real instructor PPTXs are not available on the
development VM until handover, so any concrete grouping algorithm written
now would be guesswork that the air-gapped maintainer would have to undo
later. A loud, well-documented stub is safer than a quiet, hopeful
implementation.

**Alternatives considered**:

- *Ship a heuristic that "probably works" against the mock PPTX*. Rejected —
  the mock is built to a known shape, so a heuristic that satisfies the
  mock tests is not evidence the real files will work, and a passing test
  suite would be misleading.
- *Defer the entire extractor*. Rejected — the surrounding infrastructure
  (GLC parsing, path resolution, CSV writing, logging, warning capture) is
  independent of grouping, fully testable today, and the largest chunk of
  Story 2's work.

---

## R2. Progress-test detection by filename

**Decision**: Detect progress-test presentations by a configurable
case-insensitive substring match against the PPTX filename, defaulting to
`progress_test`. Each matched file is routed to a `progress-test-N`
publication where `N` is allocated in stable, sorted-filename order so that
re-runs are deterministic.

**Rationale**: The source spec says progress-test files are clearly
identifiable by filename (section 1.11) and that the test pattern should be
configurable (section 5.2). A substring is the simplest scheme that meets
both points. Sorting filenames before allocating `N` keeps generator output
byte-identical across runs (FR-013, SC-004) without requiring the operator
to maintain a manual mapping.

**Alternatives considered**:

- *Glob pattern*. Adds a dependency on `fnmatch` semantics that is harder
  to explain in the README and rarely needed for one-shot migration work.
- *Regex pattern*. More flexible, but harder for a non-developer technical
  author to override safely on the air-gapped network.
- *Configuration file*. Overkill for a single tunable; the CLI flag is
  simpler and self-documenting via `--help`.

---

## R3. Chapter naming for the main publication

**Decision**: Derive the chapter slug from the PPTX's parent folder name,
slugified (lower-case, dashes for whitespace and underscores, ASCII only,
collapsed runs). The human-readable chapter title (used in the CSV
`chapter` column and in ditamap navtitles) is the original folder name with
title casing applied.

**Rationale**: The source spec says the chapter is "derived from
folder/filename" (section 5.2) without prescribing how. Folder names are
the natural source of truth for the `~35 folders of content` layout
(section 1.4) and this matches existing pub-9/pub-10 conventions. Using a
slug for the directory name avoids Windows path edge cases; preserving the
human-readable form for navtitles avoids surprising the technical author
during CSV review.

**Alternatives considered**:

- *Filename-derived chapters*. Rejected — multiple PPTXs may share a
  filename pattern; folder is a more reliable boundary.
- *Author-supplied mapping CSV*. Rejected — adds a manual step before
  Stage 2 with no offsetting benefit.

---

## R4. PPTX hyperlink XML access

**Decision**: Use the two access patterns documented in section 4.5 of the
spec, accessing the underlying `lxml` element via `python-pptx`'s
`._element` and `._r` accessors with the `pptx.oxml.ns.qn` namespace
helper. Wrap both accesses in small named helpers
(`extract_run_hyperlink`, `extract_shape_hyperlink`) that always return
`(target, kind)` or `(None, None)` and never raise. Both helpers are
called for every shape and every run during introspection, regardless of
shape type.

**Rationale**: Underscore-prefixed accessors are pragmatically stable in
`python-pptx` and there is no high-level alternative for shape-level click
actions. Centralising the access in named helpers means there is exactly
one place an air-gapped maintainer needs to read if hyperlink detection
breaks against an unusual file. Returning a non-raising tuple keeps call
sites uncluttered and aligns with the FR-014 no-silent-failure rule
(failures become warnings, not exceptions).

**Alternatives considered**:

- *Inline the XML lookups at every call site*. Rejected — duplicates the
  namespace plumbing across the introspector and (later) the extractor.
- *Use a different OOXML library*. Rejected — would mean a second
  third-party dependency and an entirely new API to learn on the air-
  gapped network.

---

## R5. Mock PPTX generation strategy

**Decision**: `mock_pptx.py` builds the deck with `python-pptx`'s
high-level API for slide layout, title rectangles, link text boxes, and
text-run hyperlinks. For shape-level click actions on the title rectangles
it manipulates the underlying `lxml` element directly to add an
`a:hlinkClick` element under the shape's non-visual properties, registering
the relationship via the slide's part. The vessel-name pool, link-count
variation table, and WAV-override grams are defined as named constants at
module top so the mock's structure is auditable in 30 lines of constants.

**Rationale**: Section 3.2 of the spec mandates mixing both hyperlink
mechanisms; the high-level API alone cannot attach shape-level clicks.
Constants-at-top enables the test suite (Story 5) to import the same
constants and assert against them, avoiding magic-number drift between mock
and tests.

**Alternatives considered**:

- *Hand-edit a real instructor PPTX as the test fixture*. Rejected — would
  require committing a binary fixture that no one can edit safely on the
  air-gapped network and that may carry unintended structural quirks of
  the original file.
- *XML templating without `python-pptx`*. Rejected — far more code to
  maintain than calling the library once and then patching one element.

---

## R6. GLC parsing tolerance

**Decision**: Parse GLC files with `xml.etree.ElementTree.parse` inside a
single `try` block. On `ParseError`, return a result object with empty
strings for `time_end`, `freq_end`, `image_filename` and a non-empty
`warnings` list (`"GLC malformed: <reason>"`); on missing elements,
populate what is present and add per-element warnings (`"GLC missing
bottom_crop"`, etc.); on the `<filename>` element specifically, return only
`pathlib.PureWindowsPath(raw).name` so that the broken Windows path is
discarded but the bare filename survives. All warnings flow into the
calling row's `warnings` column rather than the log alone.

**Rationale**: The spec is explicit about the `<filename>` path being
invalid (sections 1.6, 1.9), about the parser handling missing elements
gracefully (FR-005), and about every recoverable issue surfacing on the
CSV row (FR-014, SC-002). A single `try` block keeps the parser readable;
returning a structured result rather than raising keeps the call site
simple and audit-friendly.

**Alternatives considered**:

- *Schema validation with `lxml`*. Rejected — adds a second third-party
  dependency for marginal benefit; many real GLC files may be technically
  off-spec but still extractable.
- *Two-pass parsing (validate, then extract)*. Rejected — slower with no
  benefit, and `ElementTree`'s lazy access is already forgiving of order
  and unknown siblings.

---

## R7. DITA audience filtering placement

**Decision**: Use two complementary mechanisms exactly as described in the
spec:

1. *Inline `<ph audience="-trainee">` around vessel names* in topic titles
   (FR-010, section 1.10) — keeps the topic visible to trainees with the
   vessel name elided.
2. *Section-level `audience="-trainee"` attribute* on the Analysis
   Sheet section inside each gram topic — the whole instructor-only
   section is excluded by the trainee profile rather than emptied.
   (Originally framed as a topic-level attribute on a separate
   `gram_xx_analysis.dita`; the design has since collapsed to one
   topic per gram with the analysis content as a `<section>`. The
   audience-attribute mechanism is otherwise unchanged.)

The generator emits both forms; whether they end up in any particular
build is decided by the publishing toolchain's ditaval. No ditaval is
shipped with the pipeline; that file lives in the publishing project.

**Rationale**: Mirrors the existing pub-9/pub-10 convention noted in the
spec, and keeps the generator's contract narrow — it is responsible for
*marking* audience scope, not for *filtering* it. SC-005 verifies both
profiles build cleanly in Oxygen.

**Alternatives considered**:

- *Topic-level `audience` only*. Rejected — would erase the gram title for
  trainees, breaking the gram-config table layout.
- *`<ph audience>` only on analysis topics too*. Rejected — leaves an empty
  topic shell in the trainee build, which technical authors found
  confusing in pub-9 prototypes.

---

## R8. WAV row treatments

**Decision**: Treat the four `wav_treatment` values exactly as specified
(FR-011, section 6.2):

- `screenshot`: emit a normal Lofar section inside the gram's
  `gram_NN.dita` topic, identical to the PNG path.
- `gaps-lite`: emit a stub topic containing a `<note>` warning about
  GAPS-Lite dependency, an `<xref>` to the WAV path, and an XML comment
  reading `MANUAL REVIEW: GAPS-Lite required`.
- `TBD` (or empty): skip generation, log at ERROR level, append the row
  identifier to `skipped.txt`.
- Any other value: skip generation, log at ERROR level, treat as `TBD`.

The author's `wav_treatment` column is the sole authority — the generator
never infers it.

**Rationale**: WAV handling is one of the few areas where the source spec
prescribes exact behaviour per branch. Encoding it directly avoids
introducing implicit defaults that would confuse a future maintainer.

**Alternatives considered**:

- *Default empty-treatment WAVs to `screenshot`*. Rejected — the spec is
  emphatic that the technical author is the authority (Assumption 7 in
  the spec).

---

## R9. Idempotent output

**Decision**: The generator writes every output file with deterministic
content (sorted CSV row order before iteration, sorted file iteration when
walking, fixed line-ending `"\n"`, UTF-8 with no BOM, no timestamps in
generated content). It overwrites existing files unconditionally. It does
*not* delete files in the output tree that no longer correspond to a CSV
row — instead it writes a `manifest.txt` listing every file it produced,
so a maintainer can diff manifests across runs and clean up stale files
manually. A `--clean` flag clears the publication subtree before writing
when the maintainer wants fresh output.

**Rationale**: SC-004 demands byte-identical output across runs from the
same CSV. Walking and deleting unconditionally would risk wiping
hand-edited files; the manifest plus opt-in `--clean` keeps the default
safe and the destructive behaviour explicit.

**Alternatives considered**:

- *Always wipe output*. Rejected — destructive default conflicts with the
  air-gapped constraint that exception recovery is hard.
- *Hash every file and skip writes*. Rejected — unneeded complexity; a
  fresh write is fast enough at this corpus size.

---

## R10. Logging architecture

**Decision**: Each script configures `logging` at `__main__` time with two
handlers: a `StreamHandler` to stdout (level INFO) and a `FileHandler` to
the per-stage file (level DEBUG, mode `"w"` so each run starts fresh), both
sharing a one-line `%(asctime)s %(levelname)s %(name)s: %(message)s`
formatter. Module-level loggers are obtained with
`logging.getLogger(__name__)` rather than the root logger. Setup is
encapsulated in `setup_logging(log_path: Path) -> None`.

**Rationale**: FR-014 mandates dual stdout + file logging at three levels
without silent failures. Using `__name__` loggers makes filtering easy
during debugging on the air-gapped network. Keeping the setup helper short
and identical across scripts means a maintainer can read it once and
trust it everywhere.

**Alternatives considered**:

- *`basicConfig` with only a stream handler*. Rejected — fails the
  per-stage-file requirement.
- *Structured (JSON) logs*. Rejected — overkill for a one-shot tool with
  human readers on the air-gapped network.

---

## R11. CSV format

**Decision**: Use the standard library `csv` module with
`csv.DictWriter`, `quoting=csv.QUOTE_MINIMAL`, `dialect="excel"`,
`encoding="utf-8-sig"` for the output (BOM included so Excel on Windows
opens it cleanly), `lineterminator="\r\n"` to match Windows defaults.
Read in Stage 4 with `csv.DictReader` and `encoding="utf-8-sig"` so the
BOM is transparently stripped. Empty values are stored as empty strings,
not `None`.

**Rationale**: Section 1.9 of the spec dictates the column structure;
the technical author works in Excel on Windows during Stage 3. The
UTF-8 BOM is the single most reliable way to keep Excel from mangling
non-ASCII vessel names. Empty-string-not-None matches `csv.DictReader`'s
own defaults and removes one class of subtle bug.

**Alternatives considered**:

- *Plain UTF-8 without BOM*. Rejected — Excel mis-detects encoding in
  practice on Windows.
- *Tab-separated*. Rejected — the spec explicitly calls for CSV.

---

## R12. Air-gapped install path

**Decision**: The README documents two install routes for `python-pptx`:
the development-VM route (`pip install python-pptx`) and the air-gapped
route (build a wheelhouse with `pip download python-pptx -d wheels/` on
the development VM, copy `wheels/` to the air-gapped network, then
`pip install --no-index --find-links wheels/ python-pptx`). The
`requirements.txt` pins `python-pptx` to a tested version with `~=`
compatibility so wheelhouse rebuilds are predictable. No other runtime
dependency ships.

**Rationale**: The spec calls out air-gapped installation explicitly
(section 9 README requirement; section 1.2 development context). A
documented wheelhouse procedure is the standard practice and avoids the
maintainer needing to know about it.

**Alternatives considered**:

- *Vendor `python-pptx` source into the repo*. Rejected — large, hard to
  audit, complicates licensing trail.
- *Pure-stdlib OOXML parsing*. Rejected — would need to be re-derived on
  the air-gapped network if anything broke.

---

## R13. Test framework choice

**Decision**: Standard-library `unittest` with discovery
(`python -m unittest discover tests/`). No `pytest`, `coverage`, `tox`, or
fixtures-as-code library. Test fixtures are tiny files committed under
`tests/fixtures/`. The mock PPTX is generated on demand by an `unittest`
`setUpClass` (writing to `tests/_tmp/mock.pptx`) so the binary file is
not committed.

**Rationale**: FR-017 mandates `unittest`. Generating the mock at test
time avoids committing a binary fixture and keeps the test suite tight.

**Alternatives considered**:

- *Commit the mock PPTX*. Rejected — drift risk between mock generator
  and committed fixture; harder to audit.

---

## R14. Common module versus inlined helpers

**Decision**: Default to inlining short helpers (logging setup, GLC
parser, slugifier) in each script. Promote a helper to a shared
`pipeline_common.py` module only when (a) it is used by ≥3 scripts and
(b) duplication would add ≥40 lines per script. The first promotion
candidates, if any emerge, are `setup_logging`, `parse_glc`, and
`resolve_under_root`.

**Rationale**: The air-gapped maintainer's mental model is "open one file
to fix one bug." A premature shared module forces them to navigate two
files for every fix; a shared module added once duplication is real is
worth the cross-reference. This decision is recorded so a future task
that adds a shared module is doing so on purpose, not by reflex.

**Alternatives considered**:

- *Always-shared common module from day one*. Rejected — premature in a
  five-script project.
- *Always-inlined, never shared*. Rejected — would punish three identical
  copies of `parse_glc`.

---

## R15. CLI argument conventions

**Decision**: `argparse` with long-form GNU flags (`--input`, `--out`,
`--csv`, `--input-root`, `--image-root`, `--slides`, `--test-pattern`,
`--clean`). All paths accepted as strings, converted immediately to
`pathlib.Path`. Required flags are marked `required=True`. Every script
exits with code `0` on success, `1` on any unhandled error or stage
failure, `2` on `argparse` usage errors (the `argparse` default).

**Rationale**: Long flags are self-documenting on the air-gapped network
where `--help` is the only documentation an operator may have to hand.
Standardising exit codes makes the batch wrapper's `if errorlevel 1`
pattern reliable.

**Alternatives considered**:

- *`click` for richer CLI*. Rejected — adds a third-party dependency.
- *Mixing short and long flags*. Rejected — one convention is easier to
  document and remember.

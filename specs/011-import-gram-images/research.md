# Phase 0 Research: Import Author Gram Images

## R1 — Script and wrapper naming

**Decision**: Canonical script `scripts/ingest_gram_images.py`; root wrapper
`ingest.py`; log file `ingest.log`; report file `ingest_report.txt` (cwd).

**Rationale**: Follows the established wrapper↔canonical first-word pairing
(`relink.py` ↔ `relink_glc_to_image.py`, `snapshot.py` ↔
`snapshot_analysis_docs.py`). "Ingest" names the operator's mental model —
taking in an external delivery — and avoids both the Python keyword `import`
and confusion with the existing `relink` verb, which stays bound to the
same-folder `Image <N>` flow.

**Alternatives considered**: `import.py` — rejected (keyword; unimportable,
confusing). `relink2.py` / extending `relink.py` — rejected (couples two
matching grammars and two wav-disposition policies; see plan's Constitution
Check II). `match.py` — rejected (describes only phase 1).

## R2 — Duration grammar and parsing

**Decision**: The duration token is the filename's leading run up to the first
separator, matched case-insensitively against
`^(?P<m>\d+)m(?:(?P<s>\d{1,2})s)?$` → `seconds = m*60 + (s or 0)`. The stem is
everything after that separator, stripped; an empty stem is classed
unparseable. No range validation on the seconds part beyond two digits
(`5m26s` → 326, `21m` → 1260, `0m` → 0 applied as-is per spec edge case).

> **Revised (post-#145, real-data patterns):** the separator is a space **or**
> an underscore — the author uses both, sometimes after the minutes
> (`10m_0 - 600 Hz`), sometimes after the seconds (`7m20s_0 - 441 Hz`). The
> split is therefore on the first `[ _]`, not the first space.

**Rationale**: Matches the owner-confirmed grammar (`Nm`, `NmSSs`) exactly and
nothing more. Rejecting rather than guessing on other shapes feeds the
unparseable-duration survey, which is the agreed mechanism for discovering
real-world variants before extending the grammar (spec Assumptions).

**Alternatives considered**: Accepting bare seconds / `mm:ss` speculatively —
rejected: no evidence they exist, and a wrong parse silently writes a wrong
`bottom_crop` (the exact silent-miscoercion failure Principle VII warns about).
Splitting on the *last* space — rejected: stems legitimately contain spaces
(`WAV 1`), the duration is defined as the prefix.

## R3 — Matching pipeline and outcome classes

**Decision**: Three matching tiers. Comparison folds **case** but nothing else
— whitespace and token content stay exact, so genuine drift is *reported*, not
absorbed (see the post-#145 revision below):

1. **Document**: incoming `<doc>` folder name == source `<doc>` folder name.
2. **Container**: the tier holding the gram folders — the matched source doc
   folder's single subdirectory, or the doc folder itself when it holds ≥ 8
   subdirectories (a container-less flat publication); an in-between count →
   `structurally-ambiguous-doc`, doc skipped.
3. **Gram folder**: incoming `<gram>` name == a gram folder name under the
   container.
4. **Image → GLC-referenced asset**: parse each incoming image filename
   (R2); compare its stem against the *stems of assets referenced by the
   gram folder's `.glc` files* (via `parse_glc`), not directory listings.
   - referenced asset is a `.wav` whose stem equals the incoming stem →
     **match** (unique) or **ambiguous** (a second incoming image already
     claimed it).
   - referenced asset is an image whose stem equals the incoming stem →
     **already-converted** (idempotency class, not an error).
   - no referenced asset with that stem → **unmatched-image**, reported with
     the folder's available wav stems.

Full outcome taxonomy (report + tally): `matched` (verify) / `applied`
(apply), `unmatched-doc`, `structurally-ambiguous-doc`, `unmatched-gram`,
`unparseable-duration`, `unmatched-image`, `ambiguous`, `already-converted`,
`glc-unreadable`, `glc-already-cropped` (wav-backed GLC that already carries
`bitmap_crop_values`).

> **Revised (post-#145, real-data patterns):** all three name comparisons fold
> **case** — the hand-typed incoming names drift in case from `source/`
> (`7m_WAV 1.jpg` → `Wav 1.wav`), so case is never a reported mismatch. The
> `GramFolderView` buckets are keyed by the casefolded asset stem; two
> case-variant screenshots therefore collapse onto one bucket and register as
> `ambiguous`. Whitespace/token drift is still exact and still reported. When
> apply copies the image it takes the **wav's** own casing for the basename,
> not the screenshot's, keeping the folder internally consistent.

**Rationale**: Exact matching keeps the operator the sole authority on names
(Principle IV) — the report loop, not the matcher, absorbs drift. Matching
against GLC-referenced assets (not the directory) is what makes
`already-converted` detectable and post-apply verify runs clean, and it
naturally handles two GLCs referencing one wav (both rewritten, one copy).
Stem comparison is exact but extension-blind (`WAV 1` matches `WAV 1.wav`
regardless of image extension case).

**Alternatives considered**: Normalised (case/whitespace) auto-matching —
rejected by the owner during spec interview: trends may later be codified as
explicit rules, but silent absorption is never default. Matching images to
wavs present on disk — rejected: a wav no GLC references is inert; converting
it changes nothing downstream and masks delivery errors.

## R4 — Nearest-candidate suggestions and trend grouping

**Decision**: Nearest candidates via `difflib.get_close_matches(name,
candidates, n=3, cutoff=0.6)` — stdlib, deterministic. Trend grouping
classifies each mismatch against its top candidate with cheap deterministic
probes, in order: `case-only` (casefold-equal), `whitespace-only` (equal after
collapsing runs and stripping), `case+whitespace`, `token-drift` (equal token
count after whitespace split, exactly one differing token pair — reported as
`'WAVE' → 'WAV'`), else `other`. The report groups mismatches under these
labels and, for `token-drift`, aggregates identical token pairs with counts
(`'WAVE' → 'WAV' × 14`).

**Rationale**: All-stdlib, no fuzzy-matching dependency; the probe order makes
each mismatch land in exactly one class; aggregated token pairs are precisely
the "repeating trends we can handle in code" the owner asked to see. Cutoff
0.6 is difflib's default and good enough for suggestions — a miss simply
reports "no close candidate", which is itself informative.

**Alternatives considered**: Levenshtein clustering — rejected (needless
sophistication; `difflib.SequenceMatcher` underlies `get_close_matches`
anyway). Reporting a flat list only — rejected: spec FR-007 requires trend
visibility.

## R5 — Report format and location

**Decision**: Plain-text `ingest_report.txt` written to the cwd on every run
(verify and apply), sectioned by outcome class, entries sorted by path, with
per-class counts and a closing tally identical to the console summary. No
timestamps in the body (determinism); the log file carries timing. Writing the
report is the *one* write verify mode performs, and it is outside both trees.

**Rationale**: Notepad-readable on the air-gapped box (Principle I); mirrors
the `skipped.txt` precedent from the generator; cwd placement matches every
other stage artefact (`extract.csv`, `*.log`). Deterministic body keeps
re-runs diffable — the operator can diff two reports to confirm progress.

**Alternatives considered**: CSV report — rejected: this is an operator
read-and-fix artefact, not a data interchange; grouping/suggestions read
better as text. Log-only — rejected: interleaved DEBUG noise buries the
fix-up worklist.

## R6 — GLC reuse, rewrite and insertion mechanics

**Decision**: Reuse from `relink_glc_to_image.py` and `extract_to_csv.py` by
import, not duplication: `parse_glc` (read), `rewrite_glc_filename` and
`FILENAME_TAG_RE` (filename rewrite), and the dual-logging `setup_logging`
shape. The new `bitmap_crop_values` insertion is a targeted text edit in the
same style: locate the first `</filename>`, capture the leading whitespace of
the `<filename>` line, and insert

```text
\n{indent}<bitmap_crop_values>\n{indent}{unit}<bottom_crop>{N}</bottom_crop>\n{indent}</bitmap_crop_values>
```

immediately after `</filename>`, where `{unit}` is one level of the file's own
indentation (inferred from the `<filename>` line relative to its parent, else
default two spaces). Rewrite-filename and insert-crop are applied to the
in-memory text in one pass and written once — a file is never left half-edited
(anchor not found → per-file error, skip, count, no write).

**Rationale**: Byte-preserving targeted edits are the established GLC-mutation
idiom (determinism, minimal churn, no XML round-trip reordering); inserting
inside `<data_source>` after `<filename>` matches the documented schema
position, so `parse_glc` and the real GLC viewer both read it. Single-write
guards Principle VII on our own output.

**Alternatives considered**: `xml.etree` round-trip — rejected: reserialisation
churns untouched bytes (quoting, ordering, declaration), breaking the
determinism/minimal-diff invariant and risking viewer incompatibilities.
Importing from `relink_glc_to_image.py` vs copying the ~12-line helper: import
chosen; both scripts already sibling-import from `extract_to_csv`, so the
pattern exists. If review finds the cross-script import too coupled, the
fallback is documented duplication with a pointer comment — decided at
implementation, contract unaffected.

## R7 — Image copy semantics

**Decision**: `shutil.copyfile(src, dst)` (content only, no metadata), always
overwriting an existing `dst`. Destination name = wav stem + incoming image's
extension exactly as delivered (case preserved: `5m26s WAV 1.PNG` →
`WAV 1.PNG`).

**Rationale**: `copyfile` (not `copy2`) avoids copying timestamps/permissions
— byte-identical output on re-run regardless of source mtime (Principle V).
Unconditional overwrite implements the spec's stale-copy rule
deterministically. Preserving the extension's case keeps the GLC reference
and the file bit-consistent on POSIX dev hosts (case-sensitive FS) while
being harmless on the Windows target.

**Alternatives considered**: Skip-if-exists — rejected: a stale partial copy
would survive forever. Normalising extension to lowercase — rejected: churn
with no benefit; the generator's dispatch is already case-insensitive.

## R8 — Packaging and documentation impact

**Decision**: No packager change. `.github/scripts/package_release.py`
discovers wrappers by `REPO_ROOT.glob("*.py")` and canonical scripts by
`scripts/*.py` glob (with an explicit dev-only exclusion list that this script
does not join), so `ingest.py` ships under `wrappers/` and
`ingest_gram_images.py` under `scripts/` automatically. Documentation updates:
README (wrapper table, target-layout tree, "Running on the air-gapped target"
sequence — ingest sits beside `relink.py` in the prep group), CLAUDE.md
(cold-start wrapper list, one-line divergence note where relink is described).

**Rationale**: Verified by reading the packager: `WRAPPERS` and
`collect_entries()` are glob-driven. Docs are the honest-limitations surface
(Principle VI) for the wav-disposition divergence between the two relink-ish
flows.

**Alternatives considered**: None — this is a verification, not a choice.

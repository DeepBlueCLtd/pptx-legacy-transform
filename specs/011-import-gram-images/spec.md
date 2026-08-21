# Feature Specification: Import Author Gram Images

**Feature Branch**: `claude/gram-image-matching-metadata-365z6d`
**Created**: 2026-07-10
**Status**: Draft
**Input**: User description: "Import author-supplied gram images from a parallel incoming tree, matching them to wav-backed GLC files, and relink with duration metadata. Many grams have only a .wav asset; students do only visual inspection, so the author has opened each .wav in the analysis tool and taken a screenshot, saving it as `<duration> <wav-stem>.<jpg|jpeg|png>` (e.g. `5m26s WAV 1.jpg`). The incoming tree omits the source tree's intermediate container folder. A two-phase prep tool verifies the incoming tree against the source corpus (report-only), then applies the conversion: copy the image beside its GLC, repoint the GLC at it, and record the screenshot's displayed duration so downstream stages treat the gram as a pre-rendered image."

> **Partially superseded — see `contracts/ingest-contract.md`.** The duration
> metadata this spec centres on was later removed: `time_end` is measured from
> the imported image's pixel height (issue #148), so the author names the
> screenshot for the wav's own stem (no duration prefix), the whole stem is the
> match key, and apply writes only a `<filename>` repoint — no `bottom_crop`,
> no `unparseable-duration`/`glc-already-cropped` outcomes. Matching also grew a
> hyphen-spacing fold (`0 - 1000 Hz` ↔ `0-1000 Hz`) alongside the case fold, and
> demon detection now recognises numbered `Demon2-` tokens. The scenarios below
> record the original feature-011 design.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify the incoming tree against the source corpus (Priority: P1)

The technical author delivers a folder tree of screenshots taken from the
analysis tool. Its layout parallels the source corpus but omits one level:
`incoming/<document>/<gram>/` corresponds to
`source/<document>/<container>/<gram>/`, where `<container>` is the single
sub-folder of the source document folder (its name is not assumed — whatever
the one folder is called, that is the container). Folder names and image
filenames were typed by hand, so they drift from the source names (missing
spaces, `WAVE` for `WAV`, and similar). The operator runs the tool in its
default **verify** mode, which reads both trees, matches at every level, and
writes a mismatch report. The operator corrects the **incoming** tree by hand
(the source tree feeds chapter/identity extraction and must not be renamed)
and re-runs until the report is clean. Nothing on disk is modified by this
mode — the incoming tree is strictly read-only to the tool, always.

**Why this priority**: Every downstream action depends on trustworthy
matching. Hand-typed names are known to drift, and a wrong match would
silently attach the wrong spectrogram to a gram — a content error no later
stage can detect. The report loop is also the only way to discover, from real
data, which duration formats and drift patterns actually occur.

**Independent Test**: Run verify mode against a synthetic incoming tree
containing one exact match, one folder-name drift, one filename-stem drift,
and one unparseable duration prefix. The report must list each mismatch in its
own class with nearest-candidate suggestions, and no file in either tree may
change.

**Acceptance Scenarios**:

1. **Given** an incoming document folder whose name exactly matches a source
   document folder, **When** verify runs, **Then** the document is matched and
   its gram folders are checked in turn.
2. **Given** an incoming gram folder name with no exact source counterpart
   (e.g. missing a space), **When** verify runs, **Then** the report lists it
   as an unmatched gram folder together with the nearest source candidate(s).
3. **Given** an incoming image whose stem (after removing the duration token)
   matches no wav referenced by any GLC in the matched gram folder, **When**
   verify runs, **Then** the report lists it as an unmatched image with the
   wav basenames that were available to match.
4. **Given** an incoming image whose leading token cannot be read as a
   duration, **When** verify runs, **Then** the report lists it in a distinct
   "unparseable duration" class showing the raw token, so the set of formats
   in the wild is surveyed empirically.
5. **Given** several mismatches sharing a visible pattern (e.g. every `WAV n`
   typed as `WAVE n`), **When** the report is produced, **Then** those
   mismatches are grouped so the trend is visible at a glance rather than
   buried in a flat list.
6. **Given** a source document folder with an ambiguous number of sub-folders
   (neither a single container nor a large flat set of gram folders), **When**
   verify runs, **Then** the report flags that document as structurally
   ambiguous and the document is skipped for the remainder of the run.
6a. **Given** a source document folder that omits the container tier and holds
   its gram folders directly (a large flat set), **When** verify runs, **Then**
   the document folder itself is treated as the container and its gram folders
   match normally.
7. **Given** any verify run, **When** it completes, **Then** no file or folder
   in either the incoming or the source tree has been created, modified,
   renamed, or deleted.

---

### User Story 2 - Apply the conversion to verified matches (Priority: P2)

With a clean (or acceptably clean) report, the operator re-runs the tool with
an explicit **apply** flag. For every verified image↔wav match the tool: copies
the image into the source gram folder under the wav's own stem plus the
image's original extension (`WAV 1.wav` + `5m26s WAV 1.jpg` → `WAV 1.jpg`);
repoints the gram's GLC configuration at that image instead of the wav; and
records the screenshot's displayed duration, converted to whole seconds, as
the GLC's bottom-crop value (`21m` → 1260, `5m26s` → 326) — the value the
extraction stage reads as the gram's end time. The wav file is deliberately
left in place, untouched: a future user may want the audio and cannot be
assumed able to rename file suffixes; because the GLC no longer references it,
it never travels into the generated publication.

**Why this priority**: This is the payload of the feature — but it is only
safe once User Story 1 exists, and it delivers value only over verified
matches.

**Independent Test**: Run apply over a synthetic matched pair; confirm the
image copy exists beside the GLC under the wav-stem name, the GLC references
the copy, the bottom-crop value equals the duration in seconds, the wav is
byte-identical and still present, and the incoming tree is unchanged.

**Acceptance Scenarios**:

1. **Given** a verified match of `5m26s WAV 1.jpg` to a GLC referencing
   `WAV 1.wav`, **When** apply runs, **Then** the gram folder contains
   `WAV 1.jpg` (a copy of the incoming image), the GLC's referenced filename
   is `WAV 1.jpg`, and the GLC carries a bottom-crop value of `326`.
2. **Given** a duration token in whole minutes (`21m`), **When** apply runs,
   **Then** the recorded bottom-crop value is `1260`.
3. **Given** a completed apply, **When** the operator re-runs extraction and
   generation over the source tree, **Then** the converted grams flow through
   as pre-rendered image grams (embedded inline) with the recorded duration as
   their end time, and the untouched wav-only grams keep the link treatment —
   with no edits to any CSV.
4. **Given** an applied gram, **When** apply runs again over the same trees,
   **Then** the gram is skipped (its GLC already references an image) and the
   run reports it as already converted — the operation is safe to repeat
   mid-corpus.
5. **Given** a stale copy of the target image name already in the gram folder
   (e.g. from an interrupted earlier run), **When** apply runs, **Then** the
   copy is overwritten so the folder deterministically reflects the incoming
   image.
6. **Given** any apply run, **When** it completes, **Then** every wav file in
   the source tree is exactly as it was before the run, and the incoming tree
   is unchanged.

---

### User Story 3 - Ambiguities warn and defer, never guess (Priority: P3)

Real deliveries are partial and imperfect: a gram folder may hold two
screenshots for the same wav, an image for a wav no GLC references, or an
image for a gram already converted by an earlier route. The tool must never
pick a winner silently. Each ambiguous or inapplicable case is logged as a
warning, skipped, and counted in the run summary, leaving the operator to
resolve it in the incoming tree and re-run.

**Why this priority**: Protects content integrity, but only matters once the
happy paths of Stories 1–2 exist.

**Independent Test**: Construct a gram folder with two incoming images whose
stems both match one wav; run apply; confirm neither is applied, a warning
names both candidates, and the summary counts one ambiguous skip.

**Acceptance Scenarios**:

1. **Given** two incoming images that both resolve to the same wav, **When**
   the tool runs, **Then** neither is matched, a warning lists both, and the
   pair is counted as ambiguous.
2. **Given** an incoming image whose GLC already references an image (gram
   previously converted), **When** apply runs, **Then** the gram is skipped
   with a warning and nothing is modified.
3. **Given** a wav-backed GLC that unexpectedly already carries a bottom-crop
   structure, **When** apply runs, **Then** the gram is skipped with a warning
   rather than the value being overwritten or duplicated.
4. **Given** a run with any mix of applied and skipped grams, **When** it
   completes, **Then** the closing summary states the count in each outcome
   class (matched/applied, unmatched folder, unmatched image, unparseable
   duration, ambiguous, already converted, structurally ambiguous document).

---

### Edge Cases

- Source document folder has an ambiguous number of sub-folders (neither one
  container nor a large flat set) → reported as structurally ambiguous and
  skipped (US1 scenario 6). A large flat set is treated as a container-less
  publication (US1 scenario 6a).
- Incoming tree contains a document with no counterpart in the source tree at
  all → reported as an unmatched document with nearest candidates.
- Incoming gram folder is empty, or contains only non-image files → nothing to
  match; noted at debug level, not an error.
- Incoming image file for a wav that exists on disk but is referenced by no
  GLC in the gram folder → unmatched image (matching is against GLC-referenced
  wavs, not directory contents).
- Two GLCs in one gram folder reference the same wav → both are repointed at
  the single copied image; one copy, two rewrites.
- A GLC in a matched gram folder is unreadable/malformed → that GLC is skipped
  with a warning (consistent with the pipeline's forgiving boundary-parsing);
  other GLCs in the folder still process.
- The duration token parses but the stem is empty (file named only
  `5m26s.jpg`) → unparseable class (there is no stem to match).
- Image extension case variants (`.JPG`, `.Jpeg`, `.PNG`) → accepted; the copy
  keeps the incoming file's own extension spelling.
- Duration token `0m` or `0m0s` → parses to `0`; applied as-is (the value is
  the author's reading of the tool's y-axis; the tool does not second-guess
  it).
- Report is not fully clean but the operator applies anyway → apply proceeds
  over the verified subset only; everything unmatched is skipped with
  warnings, and a later re-run picks up newly fixed matches (idempotency via
  "already converted" skip).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST operate in two modes: a default report-only
  **verify** mode and an explicit opt-in **apply** mode; apply MUST never be
  the default.
- **FR-002**: The tool MUST treat the incoming tree as read-only in every
  mode, and MUST make no change of any kind to either tree in verify mode.
- **FR-003**: The tool MUST resolve each source document's gram-folder
  container by position, not by name: the *single* sub-folder of the document
  folder when there is exactly one, or the document folder itself when it holds
  a large flat set of gram folders (a threshold count, to accommodate the one
  publication that omits the container tier). A document with an in-between
  count of sub-folders MUST be reported and skipped.
- **FR-004**: The tool MUST match incoming document folders and gram folders
  to source folders by name **case-insensitively** (case drift is absorbed;
  whitespace and other differences are not), and MUST report every non-match
  together with the nearest available candidate name(s).
- **FR-005**: The tool MUST split each incoming image filename into a leading
  duration token and a remaining stem, separated by a space **or** an
  underscore, accepting duration forms of whole minutes (`Nm`) and
  minutes-plus-seconds (`NmSSs`), and MUST report filenames whose leading token
  does not parse as a distinct "unparseable duration" class that records the
  raw token.
- **FR-006**: The tool MUST match each parsed incoming image stem against the
  wav basenames referenced by the GLC files in the matched gram folder
  **case-insensitively** (not against directory listings), and MUST report
  unmatched images with the available wav names.
- **FR-007**: The report MUST group mismatches by shared pattern where one is
  detectable, so systematic drifts are visible as trends.
- **FR-008**: In apply mode, for each verified match the tool MUST copy the
  incoming image into the source gram folder named as the wav's stem (in the
  wav's own casing, not the incoming screenshot's) plus the incoming image's
  extension, overwriting an existing file of that name.
- **FR-009**: In apply mode the tool MUST repoint the matched GLC's referenced
  filename to the copied image's basename, altering nothing else in the file
  beyond the changes required by FR-010.
- **FR-010**: In apply mode the tool MUST record the parsed duration,
  converted to integer seconds, as the GLC's bottom-crop value in the
  structure the extraction stage already reads as the gram's end time.
- **FR-011**: The tool MUST leave every wav file in place and unmodified;
  conversion is expressed solely through the GLC's reference.
- **FR-012**: The tool MUST skip, warn, and count — never guess — for:
  ambiguous matches (two images to one wav), images with no matching wav, GLCs
  already referencing an image, and wav-backed GLCs already carrying a
  bottom-crop structure.
- **FR-013**: Apply MUST be idempotent: re-running over the same trees makes
  no further change, with already-converted grams skipped via the
  "GLC already references an image" rule.
- **FR-014**: Every run MUST end with a summary counting each outcome class,
  and MUST log to both the console and a per-run log file per the pipeline's
  dual-logging convention.
- **FR-015**: The tool MUST be a new, self-contained prep-time stage alongside
  the existing same-folder relink flow — neither replacing it nor changing its
  behaviour — with the same operator interface shape as the other stages (a
  thin tunable wrapper at the project root driving a canonical script).
- **FR-016**: The tool MUST accept image files with `jpg`, `jpeg`, and `png`
  extensions, case-insensitively.

### Key Entities

- **Incoming tree**: The author's delivered folder hierarchy —
  `<root>/<document>/<gram>/<images>` — read-only input; partial coverage of
  documents, grams, and lofars is normal.
- **Source document container**: The tier holding a document's gram folders —
  the single sub-folder of the document folder, or the document folder itself
  when it holds a large flat set of grams (the container-less publication);
  identified by position, never by name.
- **Candidate image**: An incoming file named `<duration> <stem>.<ext>`; its
  parsed duration supplies the bottom-crop value and its stem identifies the
  wav it replaces.
- **Duration token**: The filename's leading time reading (`21m`, `5m26s`),
  normalised to integer seconds.
- **Wav-backed GLC**: A gram-view configuration file whose referenced asset is
  a wav; the unit of conversion. After apply it references the copied image
  and carries the bottom-crop value.
- **Mismatch report**: The verify-mode output listing every unmatched
  document, gram folder, and image — with nearest candidates, an unparseable-
  duration survey, and pattern grouping — that drives the operator's manual
  fix-up loop on the incoming tree.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a delivery in which every name matches, 100% of incoming
  images are applied in a single verify-then-apply cycle with zero manual
  edits.
- **SC-002**: Every hand-typed naming drift in a delivery appears in the first
  verify report with a nearest-candidate suggestion — the operator never
  discovers a miss later by inspecting published output.
- **SC-003**: A verify run leaves both trees bit-for-bit identical to their
  pre-run state, every time.
- **SC-004**: After apply and a fresh extraction/generation cycle, every
  converted gram renders as an embedded image with its end time equal to the
  screenshot's stated duration in seconds, and every unconverted wav gram is
  unchanged in treatment — with no CSV edits performed.
- **SC-005**: Running apply twice in a row produces zero additional changes on
  the second run, and the second run's summary reports all previously
  converted grams as already converted.
- **SC-006**: No wav file is renamed, moved, altered, or deleted by any run,
  and no wav appears in the generated publication output for a converted gram.
- **SC-007**: An operator can resolve a delivery with mixed drift patterns
  using only the report (no source-tree spelunking), because mismatches are
  grouped by trend and name their nearest candidates.

## Assumptions

- The author fixes the **incoming** tree; source-tree names are never edited
  for matching purposes, because they feed chapter/identity extraction.
- Duration grammar is `Nm` or `NmSSs` (e.g. `21m`, `5m26s`), with the token
  separated from the stem by a space or an underscore (the author uses both).
  Other forms (bare seconds, `mm:ss`) are not expected; if the wild data
  disagrees, the unparseable-duration survey in the first verify report will
  reveal it and the grammar can be extended then.
- Matching folds **case** (folders and stems) because the hand-typed incoming
  names drift in case from `source/`; whitespace and token content stay exact,
  so genuine drift (missing spaces, changed words) is still reported for the
  operator to fix. A further repeating drift beyond case may still be codified
  as a normalisation rule as a follow-up rather than hand-renaming at scale.
- This is pre-CSV preparation: the operator re-runs extraction after apply, so
  no reconciliation with any in-flight signed-off CSV is needed.
- Leaving the wav in place (diverging from the existing same-folder relink
  flow, which sets the wav aside) is a deliberate product decision: future
  users may want the audio and cannot be assumed able to rename file
  suffixes. Idempotency is carried entirely by the "GLC already references an
  image" skip rule.
- Non-image files inside incoming gram folders are ignored (debug-logged
  only); the delivery may contain the author's working files.
- Project constitution constraints apply as to every stage: deterministic
  output, air-gap-debuggable operation, stdlib-only tests, and the existing
  runtime floor — detailed in the plan, not here.

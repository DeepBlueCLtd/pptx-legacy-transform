# Feature Specification: PPTX to DITA Migration Pipeline

**Feature Branch**: `claude/document-pptx-spec-xQZC8`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "this document: https://raw.githubusercontent.com/DeepBlueCLtd/pptx-legacy-transform/refs/heads/main/high-level-spec.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate DITA Publications From Reviewed CSV (Priority: P1)

A documentation team needs to convert legacy acoustic-training PowerPoint
presentations into DITA XML publications that can be rendered by a modern
browser-based spectrogram analysis tool. After a technical author has reviewed
and signed off on an intermediate CSV that captures every gram and its
measurements, the team runs the generator to produce a complete set of DITA
topics and ditamaps organised by publication and chapter, ready for the
publishing toolchain.

**Why this priority**: This is the deliverable the whole pipeline exists to
produce. Without it, the project produces no output of value to downstream
publishing. Treating it as the MVP ensures every other story is justified by
its contribution to the final DITA output.

**Independent Test**: Provide a small, hand-crafted CSV containing one row of
each topic type (GLC link, analysis PNG, WAV variants) for a main publication
and a progress-test publication. Run the generator and confirm that the
expected DITA topics, audience-filtered title fragments, and ditamaps appear
in the correct folder structure and parse as well-formed XML.

**Acceptance Scenarios**:

1. **Given** a signed-off CSV containing GLC rows for a main-publication
   chapter, **When** the generator runs, **Then** one DITA topic per gram
   is produced under `output/main/<chapter>/gram-NN/`, each containing one
   `gram-config` GramFrame table per GLC row (with the time and frequency
   values from the CSV) and an instructor-only inline phrase wrapping the
   vessel name in the title.
2. **Given** a CSV row whose topic type is `analysis`, **When** the
   generator runs, **Then** the analysis sheet is rendered as an
   instructor-only section at the top of the gram's single DITA topic —
   embedded as `<image>` when the asset is a PNG, linked via `<xref>`
   when the asset is a DOCX.
3. **Given** a CSV containing rows for a progress-test publication, **When**
   the generator runs, **Then** a flat ditamap with no chapter level is
   produced for that test publication.
4. **Given** a GLC row whose inner `data_source/filename` names a
   `.wav`, **When** the generator runs, **Then** the gram topic carries
   an `<xref>` link to the `.glc` (not the `.wav`), both the `.glc`
   and its companion `.wav` are copied next to the topic, and no
   `<image>` is emitted for that row so the on-PC GLC viewer can
   render the spectrogram from audio.
5. **Given** a GLC row whose `png_path` is empty or names an asset
   the generator cannot classify (extension other than `.png`,
   `.jpg`, `.wav`), **When** the generator runs, **Then** the row is
   skipped, an error is logged, and the row appears in a
   `skipped.txt` report.
6. **Given** the same CSV is processed twice, **When** the generator runs
   the second time, **Then** the output is byte-identical to the first run
   (idempotent).

---

### User Story 2 - Extract PPTX Content Into a Reviewable CSV (Priority: P2)

Before DITA can be generated, every gram across roughly 15 instructor PPTX
presentations and their supporting GLC files must be captured in one
intermediate dataset that a technical author can review, correct, and sign
off. The extraction step walks the content tree, identifies which
presentations are progress tests, parses each gram placeholder and its linked
GLC files, and writes one CSV row per resulting DITA topic, recording any
warnings inline so the author can triage issues in a single pass.

**Why this priority**: Without a complete and trustworthy CSV the generator
in Story 1 has nothing to consume. The CSV is also the human review gate; it
must surface every problem (missing files, malformed XML, unexpected shapes)
so that the air-gapped author can see all open questions in one place.

**Independent Test**: Point the extractor at a small fixture tree containing
one mock instructor PPTX, a per-gram supporting folder layout, and a couple
of intentionally broken GLC files. Confirm that the resulting CSV contains
the expected rows, that warnings appear on the broken-file rows, and that
the run summary lists distinct warning types.

**Acceptance Scenarios**:

1. **Given** an input root containing one main presentation and one
   progress-test presentation, **When** the extractor runs, **Then** rows
   for the main presentation are tagged with `publication=main` and a
   chapter derived from folder/filename, while rows for the progress test
   are tagged with `publication=progress-test-N` and a blank chapter.
2. **Given** a gram placeholder with four GLC links and one analysis PNG,
   **When** the extractor processes it, **Then** five rows are produced
   sharing the same `gram_id` and differing in `topic_type` and `sequence`.
3. **Given** a GLC reference whose target file cannot be found, **When**
   the extractor processes it, **Then** the row is still emitted with empty
   measurement columns and a `GLC not found` warning, and the run summary
   counts it under that warning type.
4. **Given** a malformed GLC XML file, **When** the extractor processes it,
   **Then** measurements are left blank, the failure is logged at WARNING
   level, and the row's `warnings` column records the parse error.
5. **Given** the run completes, **When** the operator reads `extract.log`,
   **Then** every PPTX processed and every GLC resolved appears at INFO
   level, and no exception is silently swallowed.

---

### User Story 3 - Introspect a PPTX to Confirm Structural Assumptions (Priority: P3)

Before the shape-grouping logic of the extractor can be implemented, an
analyst on the development VM needs an authoritative report of how real
instructor presentations are actually built: which shape types exist, how
hyperlinks are attached (shape-level versus text-run), how many shapes a
content slide really contains, and whether any slides deviate from the
assumed 3×5 grid. The introspection script renders this information as a
human-readable report so the team can confirm or adjust assumptions and
unblock the extractor.

**Why this priority**: The extractor's shape-grouping function is delivered
as a stub specifically because it depends on these findings. Until the
introspection report is in hand and reviewed, Story 2 cannot be completed.

**Independent Test**: Run introspection against the mock instructor PPTX
produced by the mock generator and confirm that the report's hyperlink
counts, extension breakdown, per-slide shape counts, and detection of both
shape-level and text-run hyperlinks match the known structure of the mock.

**Acceptance Scenarios**:

1. **Given** a PPTX file path, **When** introspection runs, **Then** a
   summary section reports total slide count, all unique hyperlink target
   extensions with counts, and the count of text-run versus shape-level
   hyperlinks.
2. **Given** a slide whose shape count deviates significantly from the
   expected count for a 15-gram layout, **When** the report is generated,
   **Then** that slide is flagged in the summary.
3. **Given** the per-slide section, **When** an analyst reads it, **Then**
   each shape's index, name, type, position in inches, truncated text,
   shape-level hyperlink target (if any), and per-run hyperlink targets are
   visible.
4. **Given** an `--out` argument, **When** introspection runs, **Then** the
   report is written to that file using UTF-8 encoding.
5. **Given** a `--slides` filter, **When** introspection runs, **Then**
   only the requested slides appear in the per-slide section.

---

### User Story 4 - Generate a Realistic Mock PPTX for Testing (Priority: P4)

Until real instructor presentations can be brought onto the development VM,
the team needs a faithful synthetic PPTX that exercises every structural
case the pipeline will encounter: a welcome slide, content slides with a
3×5 grid of gram placeholders, vessel names in titles, shape-level
hyperlinks to analysis PNGs, text-run hyperlinks to GLC files, varying
numbers of GLC links per gram, and a small number of WAV links. The mock
underpins every other test in the suite.

**Why this priority**: Mock generation is a tooling dependency for Stories
2 and 3 and for the test suite, but it does not itself deliver migration
output. It is sequenced after the value-bearing stories so that priorities
reflect deliverable value rather than implementation order.

**Independent Test**: Run the mock generator and verify with a script that
the resulting file contains the expected number of slides, exactly 15 gram
title shapes and 15 link text boxes per content slide, shape-level
hyperlinks on every title shape, text-run hyperlinks on every link box,
and the configured `.wav` links on the designated grams.

**Acceptance Scenarios**:

1. **Given** the mock generator is invoked with an output path, **When**
   it runs, **Then** a PPTX file is created with one welcome slide and the
   configured number of content slides.
2. **Given** any content slide, **When** it is inspected, **Then** it
   contains exactly 15 gram title rectangles arranged in a 3×5 grid plus
   15 corresponding link text boxes immediately below their titles.
3. **Given** any title rectangle, **When** its underlying XML is examined,
   **Then** a shape-level click action targeting an analysis PNG is
   present.
4. **Given** any link text box, **When** its runs are inspected, **Then**
   each run carries a text-run hyperlink whose target matches the
   configured `.glc` or `.wav` URI scheme.
5. **Given** the configured WAV grams, **When** their link boxes are
   inspected, **Then** the link target ends in `.wav`.

---

### User Story 5 - Run the Test Suite on the Air-Gapped Network (Priority: P5)

After deployment to the air-gapped network, a developer working without
internet access or AI assistance must be able to verify that any local edit
has not broken the pipeline. They run a single command that discovers and
executes every test in the project using only the Python standard library,
and the results clearly indicate which scripts are affected by a failure.

**Why this priority**: The tests do not produce migration output, but they
are the long-term safety net for unattended maintenance. They must work
with no third-party test framework so they remain runnable in a constrained
environment.

**Independent Test**: From a clean checkout, run the test command and
confirm that all suites discover and execute, that each script under test
has at least one passing test, and that introducing a deliberate breakage
in any script causes the corresponding test to fail with a clear message.

**Acceptance Scenarios**:

1. **Given** a working checkout, **When** the developer runs the standard
   discovery command, **Then** every test module under `tests/` is
   executed and the result reports overall pass/fail.
2. **Given** the GLC parser test, **When** it is fed minimal valid,
   element-missing, and malformed GLC fixtures, **Then** the parser's
   behaviour for each case matches the documented contract.
3. **Given** the DITA generator test, **When** it consumes a minimal CSV,
   **Then** the produced files exist at expected paths, parse as
   well-formed XML, and contain the expected audience-filtered phrase when
   a vessel name is supplied.
4. **Given** the introspection test, **When** it is run against the mock
   PPTX, **Then** the reported summary counts match the mock's known
   structure.

---

### User Story 6 - Run the End-to-End Pipeline From a Single Command (Priority: P6)

A pipeline operator on a Windows workstation needs to run the full
extraction-then-generation flow from one shortcut, with a clear pause
between stages so the technical author can review the CSV before DITA is
produced. The wrapper exits non-zero if any stage fails so that downstream
automation can detect failures.

**Why this priority**: This is convenience tooling that wraps Stories 1
and 2; it does not add new capability. It is sequenced last because the
underlying scripts must already work before there is anything to wrap.

**Independent Test**: Invoke the batch wrapper with a content root, observe
that extraction runs to completion, that the operator is prompted to
review the CSV before generation begins, and that the generation stage
produces the expected output tree on continue.

**Acceptance Scenarios**:

1. **Given** a content root path is passed as the first argument, **When**
   the wrapper is invoked, **Then** the extraction step runs against that
   root and writes the intermediate CSV.
2. **Given** extraction has completed, **When** control returns to the
   wrapper, **Then** the operator is prompted to review the CSV before the
   generation step runs.
3. **Given** any stage exits with a non-zero status, **When** the wrapper
   detects the failure, **Then** it prints an error referencing the logs
   and exits non-zero.

---

### Edge Cases

- A gram title shape's hyperlink to the analysis sheet is attached at the
  shape level on some slides and at the text-run level on others; both
  mechanisms must be detected and recorded.
- A gram folder on disk carries its analysis sheet as `Analysis Sheet.docx`
  on some grams, as `Analysis.png` on others, and rarely as both; the
  pipeline must normalise each gram folder so that both forms exist on
  disk before extraction emits the analysis CSV row. Normalisation runs
  once per gram folder, not per CSV row and not per gram instance on a
  slide, and a renderer failure on one folder must not abort the run.
- A supporting-material folder layout uses one subfolder per ten grams
  rather than one per gram; GLC path resolution must succeed for either
  layout without configuration changes.
- A GLC file's `<filename>` element points to an invalid Windows path; the
  bare filename must still be extracted and used for the DITA image href.
- A presentation contains a slide whose shape count differs significantly
  from the expected 15-gram layout; introspection must surface this rather
  than silently producing a misaligned report.
- A GLC row references an asset (via `png_path`) whose extension is
  neither a still image (`.png`, `.jpg`) nor `.wav`, or whose source
  file is missing; the generator must skip such rows with a warning
  and emit a `skipped.txt` report rather than producing partial
  output. (The historical `wav_treatment` author-decision workflow is
  retired — see backlog item 007.)
- The CSV contains a row whose `glc_path` is non-empty but cannot be
  resolved on disk; extraction must still emit the row with empty
  measurements and a recorded warning so it appears in the author's review.
- Re-running the generator over an existing output tree must overwrite
  prior files deterministically without leaving stale artefacts that would
  cause Oxygen builds to break.
- A developer on the air-gapped network must be able to run every test and
  read every error message without any tool that requires internet access
  or third-party packages beyond `python-pptx`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST consume Microsoft PowerPoint instructor
  presentations and their supporting `.glc` and image files from a single
  configurable content root and produce DITA topics and ditamaps that
  match the structure of the existing pub-9/pub-10 publications.
- **FR-002**: The pipeline MUST distinguish progress-test presentations
  from main-publication presentations by a configurable filename pattern
  and route each to a separate DITA publication, with main-publication
  output organised by chapter and progress-test output as a flat list of
  grams.
- **FR-003**: The extraction stage MUST emit one CSV row per resulting
  DITA topic, where a gram with N GLC links and one analysis PNG produces
  N+1 rows, and the unique key per row is the combination of
  publication, chapter, gram identifier, topic type, and sequence.
- **FR-004**: The CSV MUST contain the columns `publication`, `chapter`,
  `gram_id`, `vessel_name`, `topic_type`, `sequence`, `topic_filename`,
  `display_text`, `glc_path`, `time_end`, `freq_end`, `png_path`,
  `wav_treatment`, and `warnings`, with `warnings` carrying
  comma-separated issues for each row.
- **FR-005**: The GLC parser MUST extract `time_end` from the
  `bottom_crop` element, `freq_end` from the `bandwidth` element, and the
  bare filename (path stripped) from the `filename` element, and MUST
  return empty values with a recorded warning when any element is
  missing or the document cannot be parsed.
- **FR-006**: The extractor MUST resolve GLC references against the
  content folder for both the per-gram and per-ten-grams supporting
  layouts and MUST record a warning on any reference it cannot resolve,
  without aborting the run.
- **FR-007**: The introspection script MUST produce a structural report
  with a summary section (slide count, hyperlink target extensions and
  counts, shape-level versus text-run hyperlink counts, slides with
  unexpected shape counts), a per-slide section (per-shape index, name,
  type, inch-precision position, truncated text, and hyperlinks at both
  shape and run level), and a deduplicated hyperlink-target section
  grouped by extension.
- **FR-008**: The introspection script MUST detect hyperlinks attached at
  the text-run level and at the shape level (click action) for every
  shape on every slide, using both XML access mechanisms.
- **FR-009**: The mock PPTX generator MUST produce a welcome slide plus
  content slides containing exactly 15 gram placeholders each, where
  every title rectangle carries a shape-level hyperlink to an analysis
  PNG and every link text box carries text-run hyperlinks to `.glc` or
  `.wav` targets, with the configured variation in link counts per gram
  and the configured `.wav` overrides.
- **FR-010**: The DITA generator MUST emit one `gram_xx.dita` per gram
  (regardless of how many GLC rows the gram carries) containing one
  `<table outputclass="gram-config">` GramFrame block per GLC row, each
  block carrying `time-start=0`, `time-end` from CSV, `freq-start=0`,
  `freq-end` from CSV, an image reference (a topic-relative local
  filename — see FR-022), and two named `<colspec>` elements so DITA-OT
  emits `colspan="2"` on the image row (without which the GramFrame
  bundle rejects the table — see
  [`contracts/gramframe.md`](contracts/gramframe.md)). The topic carries
  a related-link back to the gram index, and a title in which the
  vessel name is wrapped in `<ph audience="-trainee">`.
- **FR-011**: The DITA generator MUST fold the analysis row into the
  same `gram_xx.dita` as an instructor-only section
  (`<section audience="-trainee">`) whose contents are an embedded
  `<image>` when the analysis asset is a PNG or an `<xref>` link when
  it is a DOCX. For each GLC row it MUST dispatch on the extension of
  the asset named in `png_path`: a `.png` or `.jpg` produces a
  GramFrame table embedding the image (`dita-topic-schema.md` §1.2);
  a `.wav` produces an `<xref>` block linking to the `.glc`
  (`dita-topic-schema.md` §1.3), with both the `.glc` and the
  companion `.wav` copied side-by-side into the per-gram folder so
  the on-PC GLC viewer can resolve the audio when a student opens
  the link; any other extension (or a missing asset) is skipped
  with a warning recorded in `skipped.txt`.
- **FR-012**: The DITA generator MUST emit one ditamap per publication,
  using `<topichead>` chapter elements with `<topicref>` children for
  the main publication and a flat `<topicref>` list for each progress-
  test publication, and MUST mirror the publication-and-chapter
  hierarchy in the output folder tree.
- **FR-013**: Re-running the generator over the same CSV MUST produce
  identical output, overwriting prior files without manual cleanup.
- **FR-014**: All scripts MUST log to both standard output and a
  per-stage log file (`extract.log`, `generate.log`) using the standard
  logging facility, at INFO level for routine progress, WARNING level
  for recoverable issues such as missing or malformed inputs, and ERROR
  level for unrecoverable failures, and MUST NOT swallow exceptions
  silently.
- **FR-015**: The shape-grouping function in the extractor MUST be
  delivered as an isolated, clearly documented stub that raises an
  explicit not-implemented error and references the introspection
  findings on which the eventual implementation depends, while every
  surrounding piece of infrastructure (GLC parsing, path resolution,
  CSV writing, logging, error handling) MUST be fully implemented.
- **FR-016**: The project MUST include a Windows batch wrapper that runs
  extraction, pauses for the technical author to review the CSV, then
  runs DITA generation, and exits non-zero on any stage failure.
- **FR-017**: The project MUST include a test suite, runnable by the
  standard-library discovery command, that covers the mock generator,
  the introspection report, the GLC parser (including
  missing-element and malformed-XML cases), and the DITA generator
  (including audience-filtered title fragments and ditamap shape for
  both main and progress-test publications), without depending on any
  third-party test framework.
- **FR-018**: The project MUST ship a README that documents context,
  prerequisites including offline installation guidance for the
  air-gapped network, the role of each script, a quickstart, a
  stage-by-stage guide highlighting what to look for during CSV review,
  a column-by-column CSV reference, troubleshooting for common warnings,
  test-suite instructions, and known limitations including the
  shape-grouping stub.
- **FR-019**: All scripts MUST adopt defensive coding practices suited to
  later air-gapped maintenance: type hints on every function signature,
  docstrings explaining purpose and limitations, named constants
  instead of inline magic values, explicit UTF-8 encoding on every file
  open, path handling via the standard pathlib facility, and no global
  mutable state.
- **FR-020**: The pipeline MUST support DITA audience filtering by
  emitting `audience="-trainee"` markers on instructor-only fragments
  (vessel names) and instructor-only topics (analysis topics), so that a
  publish step that excludes the `-trainee` audience produces
  trainee-safe output and a publish step with no exclusion produces the
  instructor output.
- **FR-021**: The README MUST include a "Publishing to HTML (optional)"
  section documenting how to acquire, install, and run DITA-OT (together
  with a Java runtime) on the air-gapped target PC so that the
  maintainer can render the generated DITA tree to HTML for sanity-
  checking without an Oxygen licence. DITA-OT and Java MUST NOT be
  bundled into the project delivery and MUST NOT become Python
  dependencies or pipeline stages; the maintainer transfers the
  installers through the air-gap manually using the README's
  instructions and invokes DITA-OT as an ad-hoc step after generation,
  separately from the automated pipeline. The README MUST also state
  that Oxygen remains the production publishing path and that the
  DITA-OT preview is for inspection only. The project MUST ship a
  `publish_html.py` helper that automates the DITA-OT invocation
  (DOCTYPE injection into a staging copy, per-ditamap rendering, output
  under a root-level `html/` tree); the script depends on Python
  standard library only and takes the DITA-OT installation path as a
  command-line argument.
- **FR-022**: The DITA generator MUST produce self-contained
  publication trees. For every topic that references an external asset
  (PNG, WAV, analysis sheet) the generator MUST copy the source asset
  into the same directory as the topic, rename the copy to match the
  topic's filename stem (e.g. the asset referenced by
  `gram_12_lofar1.dita` is copied to `gram_12_lofar1.png`), and emit
  the bare local filename as the topic's `href`. References MUST NOT
  traverse out of the chapter directory. Asset copies MUST preserve
  source modification time so that the idempotency requirement
  (FR-013) holds for the asset tree as well as the topic XML. When a
  referenced source asset is missing, the generator MUST log a warning
  and emit the topic with its intended local href anyway, so that
  dropping the asset into the source tree at the expected path and
  re-running the generator resolves the dangling reference without
  touching the topic file.
- **FR-023**: The pipeline MUST include an analysis-sheet normalisation
  stage that operates per gram *folder* (not per gram instance on a
  slide, not per CSV row) and runs before extraction emits any analysis
  row. For every gram folder under the content root, the stage MUST
  ensure both an `Analysis Sheet.docx` and an `Analysis.png` exist:
  where only the `.docx` is present it MUST be rendered to PNG via the
  configured renderer; where only the `.png` is present a minimal
  single-image `.docx` MUST be produced that embeds the PNG full-page;
  where both already exist the stage MUST leave them in place and log
  at INFO level. The stage MUST log a WARNING and continue (rather than
  abort the run) for any gram folder whose renderer step fails or whose
  renderer binary is unavailable, so that the air-gapped maintainer can
  triage affected folders from the log and from the resulting CSV row
  (where `png_path` and/or `analysis_docx_path` are left empty and the
  `warnings` column records the failure). FR-023 runs upstream of the
  FR-022 asset copy: by the time the DITA generator copies the
  `Analysis.png` next to its topic, FR-023 has guaranteed the PNG
  exists.

### Key Entities *(include if feature involves data)*

- **Source Presentation**: An instructor PPTX containing one welcome
  slide and one or more content slides; identified by filename and
  parent folder; classified as either main-publication or progress-test
  by filename pattern.
- **Gram Placeholder**: A logical unit on a content slide consisting of
  a title shape (gram identifier and vessel name, with a hyperlink to an
  analysis sheet — either an `Analysis Sheet.docx` or an `Analysis.png`
  in the gram folder; see FR-023 for the normalisation that guarantees
  both forms exist before extraction) and a link text box (one to four
  hyperlinked runs to GLC or WAV configurations); 15 placeholders are
  arranged on a 3×5 grid per content slide.
- **Analysis Sheet**: The per-gram-folder artefact describing a single
  gram's analysis, carried on disk as either `Analysis Sheet.docx` or
  `Analysis.png` (or both). One Analysis Sheet exists per gram folder,
  irrespective of how many times that gram is referenced from a slide.
  FR-023 normalisation guarantees both forms exist before extraction
  consumes the folder.
- **GLC Configuration**: An XML file describing a spectrogram analysis
  view; contributes the source-image filename, the time end (from
  bottom-crop), and the frequency end (from bandwidth) to a DITA topic.
- **Intermediate CSV Row**: One reviewable record per resulting DITA
  topic, keyed by publication, chapter, gram identifier, topic type, and
  sequence; carries display text, resolved paths, measurements, WAV
  treatment, and accumulated warnings.
- **DITA Topic**: One generated XML file per gram (`gram_xx.dita`)
  containing an instructor-only analysis-sheet section followed by one
  block per GLC row — a GramFrame `gram-config` table when the GLC
  names an image asset, or an `<xref>` link to the `.glc` when it
  names a `.wav`. The vessel name in the title is wrapped in an
  instructor-only `<ph>`, and the topic carries a related link back
  to the gram index.
- **Ditamap**: One per publication; main-publication maps use chapter
  topicheads with gram topicref children, progress-test maps are flat
  lists of gram topicrefs.
- **Publication**: A target output bucket (`main` or `progress-test-N`);
  determines folder layout and ditamap shape.
- **Chapter**: A subdivision of the main publication, derived from
  source folder or filename; absent from progress-test publications.
- **Warning**: A recoverable issue captured against a CSV row (missing
  GLC, malformed XML, unexpected shape, GLC inner asset with an
  unrecognised extension, etc.) and surfaced in the run summary so
  the technical author can triage all issues from the CSV.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The pipeline produces DITA topics for every gram across
  the full source corpus of approximately 1,000 grams in a single
  generator run with no manual intervention beyond the Stage 3 CSV
  sign-off.
- **SC-002**: A technical author can identify and triage every
  recoverable issue in the source corpus from the intermediate CSV
  alone, without rerunning extraction, because every recoverable issue
  is recorded in the row's warnings column and aggregated in the run
  summary.
- **SC-003**: A developer working on the air-gapped network, with no
  AI assistance and no internet access, can run the full test suite to
  pass/fail in under one minute on a standard development workstation
  using only the documented prerequisites.
- **SC-004**: Running the generator twice over the same signed-off CSV
  produces output trees whose corresponding files are byte-identical,
  demonstrating idempotency.
- **SC-005**: Generated DITA topics build successfully in the publishing
  toolchain (Oxygen) for both an instructor profile (no audience
  exclusion) and a trainee profile (excluding the `-trainee` audience),
  with vessel names visible only in the instructor output.
- **SC-006**: For any source PPTX or GLC that the pipeline cannot
  process, the recoverable failure is recorded against the appropriate
  CSV row or the `skipped.txt` report, and zero exceptions reach the
  console without an associated log entry.
- **SC-007**: The introspection report against a real instructor
  presentation supplies, in a single run, every piece of structural
  information needed to implement the shape-grouping stub, eliminating
  the need for further exploratory inspection before extraction is
  completed.
- **SC-008**: The mock PPTX generator produces a file that exercises
  every structural case described in the requirements (welcome slide,
  3×5 grids, varying GLC link counts, both hyperlink mechanisms, WAV
  overrides) and is accepted by every other script in the pipeline
  without special-casing.

## Assumptions

- The development VM has internet access and can install dependencies
  (notably `python-pptx`) before being moved to the air-gapped network;
  no script in the pipeline relies on network access at runtime.
- Python 3.11 or later is available on both the development VM and the
  air-gapped target environment.
- Source content lives under a single configurable root on a Windows
  filesystem; the analyst network's drive letter and folder layout do
  not change between extraction runs.
- Approximately 15 instructor presentations and roughly 1,000 grams
  exist in scope; student-version presentations are not processed.
- Each content slide hosts exactly 15 gram placeholders in a 3×5 grid
  unless introspection reports otherwise; introspection findings are
  authoritative for any deviation.
- The exact mechanism by which a gram title shape carries its analysis-
  PNG hyperlink (shape-level click action versus text-run hyperlink) is
  not assumed in advance; the introspection report is the source of
  truth used to finalise the extractor's shape-grouping logic.
- Progress-test presentations are clearly identifiable by filename and
  the matching pattern can be expressed as a substring or simple glob
  configurable at run time.
- The technical author performing Stage 3 review is comfortable editing
  CSV in a spreadsheet tool. The author has no decisions to make about
  WAV-typed GLC rows: the generator dispatches on the extension of the
  asset named inside the `.glc` and treats audio assets as
  GLC-viewer links (see FR-011 and `dita-topic-schema.md` §1.3).
- The publishing toolchain (Oxygen) is available outside this pipeline
  for Stage 5 QA and is the production HTML publishing path; the
  pipeline's contract ends at producing DITA topics and ditamaps that
  conform to the existing pub-9/pub-10 structure. DITA-OT is available
  separately on the air-gapped target PC as an installed-by-the-user
  toolchain (with a Java runtime) and offers a development/maintenance
  HTML-preview path documented in the README, but it is not bundled in
  the delivery and is not part of the automated pipeline.
- `python-pptx` is the only third-party dependency; the test suite uses
  only the Python standard library.
- DITA audience filtering uses the existing convention `audience="-trainee"`
  to mark instructor-only content, consistent with the target
  publications.
- A renderer capable of converting `.docx` to PNG is available on both
  the development VM and the air-gapped target PC (LibreOffice headless
  is the default expectation; an equivalent that exposes a
  command-line `.docx → image` conversion is acceptable). The renderer
  binary is discoverable on PATH or via a configurable command. It is
  used only by the FR-023 normalisation stage and never at runtime by
  any other stage; like DITA-OT (FR-021) it is installed-by-the-user,
  documented in the README, and not bundled in the project delivery.

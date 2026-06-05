# Feature Specification: Analysis-Sheet Images (render Word analysis sheets to PNG)

**Feature Branch**: `007-analysis-sheet-images`
**Created**: 2026-05-29
**Status**: Draft
**Input**: User description: "Render legacy analysis-sheet Word documents (.doc and .docx) to PNG images so the gram's analysis table is embedded inline in the DITA topic instead of forcing the instructor to open MS Word. The Word 'tables' are visually-aligned text blocks rather than real tables, so a logical parse would corrupt them — a page render is the robust representation. Use LibreOffice headless as a prep-time, render-once snapshot stage (the FR-023 idea already sketched in spec 001), extended to cover legacy binary .doc as well as .docx. The PNG becomes a committed source asset copied deterministically downstream; the renderer never runs inside a re-runnable loop. Air-gapped Windows target, one runtime Python dependency (python-pptx), stdlib-only tests."

## Context & Motivation *(informative)*

Many grams in the target publication carry their analysis sheet as a
landscape Word document (`analysis table.doc` in the older decks; a
`.docx` in newer ones). When an instructor opens such a gram, the
analysis sheet only appears after MS Word launches and loads the file —
a noticeable delay that interrupts the lesson. Grams whose analysis
sheet is already a PNG show the table instantly, embedded in the page,
and are markedly more intuitive to use.

The analysis sheets are, without known exception, a single landscape
page containing one analysis table. Critically, those "tables" are laid
out as **text blocks aligned by eye**, not as real word-processor
tables with row/column structure. Any attempt to parse the table
*logically* (extracting cells and re-emitting a structured table) would
therefore silently corrupt the alignment. Rendering the page to an
image preserves exactly what the author laid out and exactly what the
instructor expects to see.

This feature realises and extends the analysis-sheet snapshotting idea
already sketched as **FR-023** in `specs/001-pptx-dita-migration`
(which covered `.docx` only). The extension is to also accept the
**legacy binary `.doc`** format that the older decks use, and to make
"every analysis sheet is available as a PNG" the guaranteed outcome so
the DITA generator embeds it inline for every gram.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Analysis table shows instantly, inline (Priority: P1)

An instructor opening any gram sees its analysis table rendered inline
on the page as an image, with no wait for MS Word to launch — the same
fast, intuitive experience the PNG-backed grams already provide.

**Why this priority**: This is the entire point of the feature — the
Word-launch delay is the problem being solved, and inline display is the
value delivered. Without it, nothing else matters.

**Independent Test**: Take a gram folder whose analysis sheet is a Word
document, run the pipeline end-to-end, and confirm the published topic
embeds the analysis table as an inline image rather than a click-to-open
link to a Word file.

**Acceptance Scenarios**:

1. **Given** a gram folder whose analysis sheet is a Word document,
   **When** the pipeline runs, **Then** the gram's topic embeds the
   analysis sheet as an inline image (not a link the instructor must
   click to open in Word).
2. **Given** a gram folder whose analysis sheet is already a PNG,
   **When** the pipeline runs, **Then** the existing PNG is used
   unchanged and the topic embeds it inline exactly as before.
3. **Given** the rendered analysis image, **When** an instructor views
   the gram, **Then** the table's visual alignment matches the original
   Word document's single landscape page.

---

### User Story 2 - Legacy `.doc` decks are covered, not just `.docx` (Priority: P1)

A maintainer processing the older instructor decks — whose analysis
sheets are legacy binary `.doc` files — gets the same inline-image
outcome as the newer `.docx`-based decks, with no manual conversion
step.

**Why this priority**: The bulk of the affected, slow-to-open grams are
in the older `.doc` decks. Covering only `.docx` would leave the
original problem largely unsolved. This is co-equal P1 with Story 1.

**Independent Test**: Point the snapshot stage at a content tree
containing `.doc` analysis sheets and confirm a PNG is produced for each
without any pre-conversion of the `.doc` files by hand.

**Acceptance Scenarios**:

1. **Given** a gram folder whose analysis sheet is a legacy binary
   `.doc`, **When** the snapshot stage runs, **Then** a PNG of the
   document's landscape page is produced beside it.
2. **Given** a gram folder whose analysis sheet is a `.docx`, **When**
   the snapshot stage runs, **Then** a PNG is produced exactly as
   for the `.doc` case.
3. **Given** a content tree mixing `.doc`, `.docx`, and pre-existing
   `.png` analysis sheets, **When** the stage runs, **Then** every gram
   folder ends with a usable analysis PNG regardless of its original
   form.

---

### User Story 3 - Failures are visible, never fatal (Priority: P2)

A maintainer running the pipeline on the air-gapped network can tell, at
a glance from the logs and the review CSV, exactly which analysis sheets
failed to render — without the whole run aborting and without losing the
other grams' output.

**Why this priority**: The air-gapped target has no AI assistance and no
internet for troubleshooting. A render that aborts the batch, or fails
silently, would be far costlier to diagnose than one that degrades
gracefully and is surfaced in the existing review trail. Important, but
secondary to producing the images in the first place.

**Independent Test**: Run the stage with the renderer made unavailable
(or pointed at a deliberately failing command) and confirm the run
completes, every failure is logged as a warning, the affected grams are
flagged in the CSV, and the un-affected grams are produced normally.

**Acceptance Scenarios**:

1. **Given** a renderer that is unavailable or returns an error for one
   folder, **When** the stage runs, **Then** that folder is logged as a
   WARNING, the run continues to the remaining folders, and the run
   exits successfully.
2. **Given** a gram whose analysis PNG could not be produced, **When**
   the review CSV is generated, **Then** that gram's row records the
   failure so the maintainer can triage it.
3. **Given** a gram whose analysis PNG could not be produced, **When**
   the DITA is generated, **Then** the topic still emits with its
   intended local image reference (dangling), so that dropping the PNG
   in later and re-running resolves it without churning the topic XML.

---

### Edge Cases

- **Multi-page Word document**: the analysis sheets are expected to be a
  single landscape page. If a document spans more than one page, the
  stage renders the first page and logs a WARNING noting the extra
  pages were not captured, so the maintainer can review it.
- **Both a Word document and a PNG already present** in the same gram
  folder: the existing PNG is treated as authoritative and left
  unchanged (no re-render), logged at INFO.
- **Re-running over an already-processed tree**: the stage is a no-op
  for any gram that already has its PNG — it does not re-render, so
  output (including the image bytes already committed) does not churn.
- **Corrupt or password-protected Word document**: treated as a render
  failure — WARNING logged, run continues, gram flagged in the CSV.
- **Analysis sheet missing entirely** (no Word document and no PNG): a
  WARNING is logged and the run continues; the gram's topic dangles its
  image reference per the existing missing-asset behaviour.
- **Analysis-sheet filename variation** (e.g. `analysis table.doc` vs
  `Analysis Sheet.docx`): the stage identifies the analysis sheet by its
  role and extension case-insensitively, covering the real-corpus naming
  rather than a single hard-coded filename.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pipeline MUST be able to produce a PNG image of a
  gram's analysis sheet from a Word-document source, so the analysis
  table can be embedded inline in the gram's topic.
- **FR-002**: The PNG-production step MUST accept both legacy binary
  `.doc` and Open XML `.docx` analysis sheets as input. (This extends
  spec 001's FR-023, which covered `.docx` only.)
- **FR-003**: The step MUST render the document **as a page image** and
  MUST NOT attempt to parse the analysis table into structured cells,
  because the source "tables" are visually-aligned text blocks whose
  alignment a logical parse would corrupt.
- **FR-004**: The rendered image MUST faithfully reproduce the single
  landscape page the author laid out (its visual alignment), at a
  legibility comparable to the existing pre-rendered analysis PNGs.
- **FR-005**: Where a gram folder already contains an analysis PNG, the
  step MUST use it unchanged and MUST NOT re-render from the Word source.
- **FR-006**: The step MUST be **render-once at preparation time**: the
  produced PNG becomes a committed source asset that downstream stages
  copy deterministically. The renderer MUST NOT run inside any
  re-runnable generate/publish loop, so that repeat runs over an
  unchanged source remain byte-identical (preserving the project's
  determinism/idempotency invariant).
- **FR-007**: Re-running the step over a tree that already has its PNGs
  MUST be a no-op (no re-render, no byte churn) and MUST log per-gram at
  INFO level.
- **FR-008**: A render failure or an unavailable renderer for any gram
  MUST be logged as a WARNING and MUST NOT abort the run; the stage MUST
  continue to the remaining gram folders and exit successfully.
- **FR-009**: Grams whose analysis PNG could not be produced MUST be
  surfaced in the review CSV (the affected row recording the failure),
  so the technical author/maintainer can triage them from the existing
  hand-off artefact.
- **FR-010**: When an analysis PNG is absent at generate time (because
  rendering failed or the asset is missing), the generator MUST still
  emit the topic with its intended local image reference, so that
  supplying the PNG later and re-running resolves the reference without
  modifying the topic XML.
- **FR-011**: The step MUST write a DEBUG log file at the repository root
  alongside console output, consistent with the other pipeline stages'
  dual-logging convention, as the primary debugging surface on the
  air-gapped network.
- **FR-012**: The step MUST NOT add a third-party dependency to the
  pipeline's **runtime** path, and the project's **tests** MUST remain
  standard-library only. The prep-time snapshot step MAY use
  maintainer-installed prep tooling (the Word→image renderer of FR-013,
  and the image-processing capability of FR-017); any such tooling MUST
  be imported/invoked only by this prep step, MUST degrade gracefully
  when absent, and MUST NOT be required by the runtime stages
  (`extract_to_csv.py`, `generate_dita.py`, `publish_html.py`) or by the
  test suite.
- **FR-013**: The renderer used to convert Word documents to images MUST
  be configurable (so an equivalent command can be substituted) and its
  acquisition, install, and air-gap-transfer instructions MUST be
  documented for the maintainer.
- **FR-014**: The step MUST emit an end-of-run summary (e.g. documents
  seen, documents rendered, already-present PNGs skipped, render
  failures, multi-page warnings) so the maintainer can confirm the
  outcome at a glance.
- **FR-015**: The step MUST select analysis documents by the corpus
  naming convention (filename containing `analysis`, case-insensitive)
  combined with a `.doc`/`.docx` extension. Analysis documents share the
  chapter folder with PPT source data and other Word documents, so the
  step MUST NOT render every Word document it encounters — only those
  matching the analysis-sheet naming convention.
- **FR-016**: The step MUST render the document's first page as the
  analysis image AND MUST detect when a source document has more than one
  page; on a multi-page source it MUST still produce the first-page image
  but MUST log a WARNING and flag the affected gram (so the row is
  surfaced in the review CSV) — a multi-page sheet MUST NOT be silently
  truncated.
- **FR-017**: The step MUST produce a tidy inline image: it MUST trim the
  surrounding page margins (whitespace) and normalise the output
  resolution so the analysis table displays cleanly inline at a
  legibility comparable to the existing pre-rendered analysis PNGs. This
  post-processing MUST degrade gracefully — if the image-processing
  capability is unavailable on the host, the step MUST fall back to the
  untrimmed full-page render (logging that it did so) rather than fail.
- **FR-018**: The pipeline MUST guarantee that every analysis sheet
  exists in **both** forms — an image (`.png`) for inline display and a
  Word document (`.docx`) — so a downstream consumer that needs the Word
  form always finds one. Where only an image exists, the step MUST
  produce a minimal `.docx` that embeds that image full-page; where only
  a Word document exists, the rendered `.png` (FR-001) already satisfies
  the image side. This reverse wrapping MUST use the project's existing
  standard-library document-authoring approach (no new dependency) and
  MUST be deterministic (idempotent, byte-stable across runs).

### Key Entities *(include if feature involves data)*

- **Analysis Sheet**: The artefact describing a single gram's analysis —
  a single landscape page. It lives in the chapter folder alongside other
  files (PPT source data, unrelated Word documents) and follows the
  `*analysis*` naming convention. On disk it originates as a legacy
  `.doc`, a `.docx`, or a pre-existing `.png`. After snapshotting it
  exists in both an image and a Word form (FR-018).
- **Analysis Image**: The PNG rendering of an Analysis Sheet's first
  page, margin-trimmed and resolution-normalised (FR-017). Once produced
  it is a committed source asset, copied beside the gram's topic by the
  downstream generator and embedded inline.
- **Chapter Folder**: The on-disk folder holding a chapter's files,
  including analysis documents mixed with other content. The snapshot
  step scans it for analysis documents by name pattern (FR-015), not by
  rendering every file present.
- **Review CSV Row**: The technical-author hand-off record for a gram;
  carries the analysis image path and any render-failure / multi-page
  warning so issues are visible without reading the logs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of analysis documents (`*analysis*.doc`/`.docx`) end
  up with an analysis PNG available for inline embedding, except those
  explicitly flagged as render failures; and 100% of analysis sheets end
  up with both an image and a `.docx` form (FR-018).
- **SC-002**: Across a representative corpus, the proportion of grams
  whose analysis table opens instantly inline (rather than via a Word
  launch) rises from today's PNG-only subset to effectively all grams
  with a renderable analysis sheet.
- **SC-003**: An instructor viewing a gram sees the analysis table with
  no MS-Word launch step — the table is present the moment the page is
  open.
- **SC-004**: Running the full pipeline twice over an unchanged source
  tree yields byte-identical output, including the analysis images.
- **SC-005**: When some analysis sheets cannot be rendered, the run
  still completes successfully, produces every other gram's output, and
  lets the maintainer identify 100% of the failures from the logs and
  the review CSV without further investigation.
- **SC-006**: A maintainer can identify which analysis documents failed
  to render, or spanned more than one page, in under one minute by
  reading the end-of-run summary.

## Assumptions

- **Both forms are guaranteed.** This feature guarantees every analysis
  sheet is available as a PNG for inline embedding **and** as a `.docx`
  (FR-018) — the bidirectional shape from spec 001's FR-023, now in
  scope. The image side is the headline (it solves the Word-launch
  delay); the `.docx` side is the reverse wrapper for any sheet that
  exists only as an image.
- **The source is one landscape page with one visually-laid-out table**,
  per the user's "without exception" observation. Multi-page documents
  are handled by rendering the first page **and** warning + flagging the
  gram (FR-016) — never silently truncated. Full multi-page → multi-image
  rendering is not built (the corpus is single-page); the warning exists
  to catch any exception to that.
- **The image post-processing capability (margin-trim + DPI, FR-017) may
  rely on a second prep-time library.** The project's hard rule is one
  *runtime* dependency and standard-library *tests*; this capability is
  used only by the prep-time snapshot step, is imported defensively
  (the step falls back to the untrimmed full-page render and logs when it
  is unavailable), and is never imported on the pipeline's runtime path
  or by the test suite. It is documented as an installed-by-the-maintainer
  prerequisite like the renderer, not bundled.
- **A renderer that converts Word documents (both `.doc` and `.docx`) to
  a page image is available** on both the development machine and the
  air-gapped target, installed by the maintainer and documented in the
  README — consistent with how DITA-OT is treated. LibreOffice headless
  is the default expectation; an equivalent command-line `.doc/.docx →
  image` converter is acceptable via the configurable renderer command.
- **The renderer is a preparation-time tool, not a runtime dependency.**
  It runs once to produce committed source images and is never invoked
  by the re-runnable generate/publish stages, so it does not affect the
  one-runtime-dependency or determinism invariants.
- **Analysis-sheet image bytes need only be deterministic once produced
  and committed**, not reproducible from scratch on every machine; the
  determinism invariant is satisfied by treating the rendered PNG as a
  committed source asset that downstream stages copy byte-for-byte.
- **Filenames vary across decks** (`analysis table.doc`, `Analysis
  Sheet.docx`, `*ANALYSIS.png`, …); the analysis sheet is identified by
  role and extension case-insensitively. The exact real-corpus filename
  conventions should be confirmed against an introspection report from a
  real instructor deck before final implementation.
- **This feature builds on the unimplemented FR-023 stage**, not on a
  shipped one; delivering this feature implements that snapshot
  stage (extended to `.doc`) for the first time.

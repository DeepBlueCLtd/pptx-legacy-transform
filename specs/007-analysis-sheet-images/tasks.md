# Tasks: Analysis-Sheet Images (render Word analysis sheets to PNG)

**Input**: Design documents from `/specs/007-analysis-sheet-images/`
**Prerequisites**: plan.md (required), spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are INCLUDED — the project's air-gapped contract (CLAUDE.md,
constitution Principle III) makes the stdlib-`unittest` suite the canonical
verification surface, and the plan's Testing section names a new module
(`tests/test_normalise_analysis_sheets.py`), extensions to
`tests/test_extract_to_csv.py`, and updates to two existing tests the change
breaks (`tests/test_run_pipeline_bat.py`, `tests/test_mock_pptx.py`).

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing. All paths are repository-root relative (flat-script
layout per features 001–006). New runtime-critical code is stdlib-only; the
LibreOffice renderer is stubbed in tests via `--renderer-cmd`; Pillow (FR-017) is
defensively imported and its crop test is `skipUnless(PIL)`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Each task names the exact file path it touches

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the new script skeleton and the shared test stub later
phases build on. No behaviour change yet.

- [X] T001 Create `normalise_analysis_sheets.py` at repo root following the
  `verb_noun.py` / `main(argv) -> int` + `argparse` + `setup_logging(Path("normalise.log"))`
  pattern of `extract_to_csv.py` (`from __future__ import annotations`, stdlib-only
  runtime path, Python 3.9 floor). Wire `--content-root` (required),
  `--renderer-cmd` (default `"soffice"`), `--dry-run` (flag) per
  `specs/007-analysis-sheet-images/contracts/normalise-cli.md`; leave the scan/render
  body as a documented TODO returning exit 0. Exit codes 0/1/2 per the contract.
- [X] T002 [P] Add a renderer stub script `tests/fixtures/fake_renderer.py` that
  mimics `soffice --headless --convert-to {png|pdf} --outdir <dir> <doc>`: parse the
  args, and for `--convert-to png` write a tiny valid PNG (reuse the byte template
  from `mock_pptx.py:emit_png`, importing it) named after the input stem into
  `--outdir`; for `--convert-to pdf` write a minimal single-page PDF (a `/Count 1`
  page-tree) so `page_count` reads 1. Used by tests via `--renderer-cmd`, keeping
  the suite LibreOffice-free (research R6).

**Checkpoint**: `python normalise_analysis_sheets.py --content-root <empty-dir>`
runs, writes `normalise.log`, exits 0.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The analysis-document **selection rule** (FR-015) and the
render-once **classification** every later phase depends on. This is the guard
that prevents rendering unrelated Word files in the chapter folder.

- [X] T003 In `normalise_analysis_sheets.py`, implement
  `iter_analysis_sheets(content_root: Path) -> Iterator[Path]`: walk the tree and
  yield every file whose **name contains `analysis` (case-insensitive)** AND whose
  suffix is `.doc`/`.docx`, in deterministic sorted order. It MUST NOT yield other
  Word documents (e.g. `source_data.doc`) sharing the chapter folder (FR-015,
  research R7).
- [X] T004 In `normalise_analysis_sheets.py`, implement
  `needs_render(doc: Path) -> bool` returning `True` iff no same-stem `.png`
  sibling exists (`doc.with_suffix(".png")`), and a `NormaliseResult` dataclass
  (`source_path`, `outcome`, `multipage: bool`, `tidied: bool`, `docx_wrapped: bool`,
  `warning: str | None`) per `data-model.md §2`.

**Checkpoint**: selection + classification are unit-testable (covered in T011);
no rendering yet.

---

## Phase 3: User Stories 1 & 2 — doc/docx → inline image (Priority: P1) 🎯 MVP

**Goal**: An analysis sheet authored as `.doc` *or* `.docx` ends up rendered to a
sibling `.png` that the generator embeds inline — the fast, no-Word-launch
experience. US1 (inline image) and US2 (`.doc`+`.docx` coverage) are co-equal P1
and share these code paths.

**Independent Test**: Run `normalise_analysis_sheets.py` (renderer = the T002
stub) over a tree with a `*analysis*.doc` and a `*analysis*.docx`; confirm each
gains a sibling `.png`. Then extract + generate and confirm the gram topic embeds
an inline `<image>`, not a Word `<xref>`.

### Tests for US1 & US2 (write first)

- [X] T005 [P] [US1] In `tests/test_normalise_analysis_sheets.py` add
  `test_doc_only_folder_produces_png`: temp folder with only `aaa_analysis.doc`
  (placeholder bytes), run `main` with `--renderer-cmd` → the T002 stub, assert a
  same-stem `.png` now exists and exit code 0.
- [X] T006 [P] [US2] In `tests/test_normalise_analysis_sheets.py` add
  `test_docx_only_folder_produces_png`: as T005 but `bbb_analysis.docx`.
- [X] T007 [P] [US1] In `tests/test_normalise_analysis_sheets.py` add
  `test_png_already_present_is_noop`: folder with `ccc_analysis.doc` + an existing
  `ccc_analysis.png`; assert no re-render (PNG mtime unchanged), one INFO line,
  outcome `skipped_has_png` (idempotency / determinism, research R2).
- [X] T008 [P] [US2] In `tests/test_normalise_analysis_sheets.py` add
  `test_non_analysis_word_doc_not_rendered`: folder with `source_data.doc`
  alongside `ddd_analysis.doc`; assert only `ddd_analysis.png` is produced and
  `source_data` is untouched (the FR-015 selection guard).
- [X] T009 [P] [US1] In `tests/test_extract_to_csv.py` add
  `test_analysis_doc_redirects_to_sibling_png`: an analysis hyperlink targeting a
  `.doc`/`.docx` with a sibling `.png` present → the analysis row's `png_path`
  ends `.png`, `target_ext == ".png"`, no warning.

### Implementation for US1 & US2

- [X] T010 [US1] In `normalise_analysis_sheets.py`, implement
  `render_doc_to_png(doc: Path, png_out: Path, renderer_cmd: str) -> bool` via
  `subprocess.run([renderer_cmd, "--headless", "--convert-to", "png", "--outdir",
  <tmp>, str(doc)])`, then move the produced PNG to `png_out` (same-stem sibling).
  Return `True` on success. NEVER raises (failure handling lands in T015).
- [X] T011 [US1] In `normalise_analysis_sheets.py`, implement the `main()` scan
  loop: for each `iter_analysis_sheets` result, if `needs_render` → render (T010);
  else record `skipped_has_png` (INFO). Honour `--dry-run` (log intent, write
  nothing). Accumulate `NormaliseResult`s. This makes T005–T008 pass.
- [X] T012 [US2] In `extract_to_csv.py` `gram_to_rows` analysis-row block
  (around L851–877), after `resolve_asset_path`, if the resolved suffix is
  `.doc`/`.docx` redirect `analysis_png_resolved` to its same-stem `.png`
  (recompute `target_ext`/`file_size` from the `.png`). `.png`/`.jpg` hyperlinks
  unchanged; `CSV_COLUMNS` unchanged. Makes T009 pass. (FR-004)
- [X] T013 [P] [US2] In `mock_pptx.py`, extend the analysis-sheet mix at L540 from
  `("docx", "png")` to `("doc", "docx", "png")`; for the new `"doc"` kind write
  `<stem>_analysis.doc` (placeholder bytes via a new tiny `emit_doc` helper, or
  reuse `emit_docx` bytes under a `.doc` name) AND its rendered sibling
  `<stem>_analysis.png` (via `emit_png`), so full-pipeline tests exercise the
  doc→inline path without LibreOffice. Keep emitted bytes deterministic.
- [X] T014 [US1] Update `run_pipeline.bat`: insert
  `python normalise_analysis_sheets.py --content-root %1` as a new first stage
  before the extract step, with `if errorlevel 1 goto error`. New order:
  normalise → extract → pause → generate. (FR-006)

**Checkpoint**: MVP complete — `.doc`/`.docx` analysis sheets render to PNGs and
embed inline; `generate_dita.py` and the DITA shape are untouched.

---

## Phase 4: User Story 3 — failures visible, never fatal (Priority: P2)

**Goal**: Render failures, an unavailable renderer, and multi-page sources are
WARNINGs that defer (run continues, exit 0) and are surfaced in `normalise.log`,
the end-of-run summary, and the review CSV — never an abort, never a silent
truncation.

**Independent Test**: Point `--renderer-cmd` at a script that exits 1; confirm
the run completes (exit 0), the failure is logged + summarised, and the affected
analysis row carries a warning. Separately, feed a multi-page source and confirm
a page-1 PNG + a WARNING (not a truncation).

### Tests for US3 (write first)

- [X] T015 [P] [US3] In `tests/test_normalise_analysis_sheets.py` add
  `test_renderer_failure_is_warning_not_abort`: `--renderer-cmd` → a stub that
  exits 1; assert outcome `render_failed`, a WARNING logged, run exit 0, and the
  summary records the failure.
- [X] T016 [P] [US3] In `tests/test_normalise_analysis_sheets.py` add
  `test_multipage_source_warns_not_truncates`: stub returns a `/Count 2` PDF for
  `--convert-to pdf`; assert the page-1 PNG is still produced, `multipage=True`,
  and a WARNING is logged (FR-016, research R3).
- [X] T017 [P] [US3] In `tests/test_extract_to_csv.py` add
  `test_analysis_doc_without_png_records_warning`: `.doc` hyperlink, sibling `.png`
  absent → `png_path` still the intended `.png` path, `warnings` contains
  `"analysis image not rendered"` (dangling image, not an `<xref>`). (FR-009/FR-010)

### Implementation for US3

- [X] T018 [US3] In `normalise_analysis_sheets.py`, make `render_doc_to_png`
  (T010) log a WARNING and return `False` on non-zero exit / `FileNotFoundError`
  (renderer absent), and have `main` record `render_failed` and continue. NEVER
  raises. (FR-008)
- [X] T019 [US3] In `normalise_analysis_sheets.py`, implement
  `page_count(doc, renderer_cmd) -> int | None` via a companion
  `--convert-to pdf` + a tolerant stdlib read of the PDF page-tree `/Count`;
  in `main`, when count > 1 still keep the page-1 PNG but set `multipage=True` and
  log a WARNING; when count is undeterminable, log a softer "page count
  undetermined" WARNING (never silent). (FR-016, research R3)
- [X] T020 [US3] In `normalise_analysis_sheets.py`, implement the end-of-run
  summary (logged + printed): `sheets_seen`, `rendered`, `skipped_has_png`,
  `render_failed`, `multipage_warned`, `docx_wrapped`, `tidy_skipped`. (FR-014)
- [X] T021 [US3] In `extract_to_csv.py` analysis-row block, when the redirected
  `.png` does not exist on disk, append `"analysis image not rendered"` to the
  row `warnings` (keep `png_path` as the intended `.png` so the generator dangles
  the image, not an `<xref>`). Makes T017 pass. (FR-009, FR-010)

**Checkpoint**: failures and multi-page sources are visible and non-fatal end to
end.

---

## Phase 5: Image quality — margin-trim + DPI (FR-017)

**Goal**: The rendered PNG is trimmed of page-margin whitespace and
DPI-normalised for tidy inline display, via a **defensively-imported** Pillow,
falling back to the full-page render when Pillow is absent — without ever failing
or requiring Pillow in the test suite.

### Tests (write first)

- [X] T022 [P] In `tests/test_normalise_analysis_sheets.py` add
  `test_tidy_falls_back_without_pillow`: simulate Pillow absent (e.g. monkeypatch
  the guarded import to raise `ImportError`); assert the full-page PNG is kept,
  `tidied=False`, an INFO line is logged, and the run still exits 0.
- [X] T023 [P] In `tests/test_normalise_analysis_sheets.py` add
  `test_tidy_crops_when_pillow_present` under
  `@unittest.skipUnless(<PIL importable>, "Pillow not installed")`: a PNG with a
  white border is cropped smaller and `tidied=True`. Keeps the canonical suite
  green without Pillow.

### Implementation

- [X] T024 In `normalise_analysis_sheets.py`, implement `tidy_image(png: Path) ->
  bool`: `try: from PIL import Image, ImageChops` inside the function; compute the
  non-white bounding box, crop with a small fixed margin, set DPI on save, in
  place. On `ImportError` or any processing error: log once and leave the
  full-page PNG untouched, return `False`. NEVER raises. (FR-017, research R8)
- [X] T025 In `normalise_analysis_sheets.py`, call `tidy_image` in `main` right
  after a successful render (not on `skipped_has_png`), recording `tidied`/
  `tidy_skipped` in the result and summary.

**Checkpoint**: rendered images are tidy where Pillow is available, full-page
otherwise; suite is green with and without Pillow.

---

## Phase 6: Both-forms guarantee — reverse PNG→.docx wrap (FR-018)

**Goal**: Every analysis sheet exists in both an image and a `.docx` form. For a
sheet that is PNG-only, emit a minimal full-page `.docx` using the stdlib
`zipfile`+`xml.etree` approach (no dependency), byte-stable and idempotent.

### Tests (write first)

- [X] T026 [P] In `tests/test_normalise_analysis_sheets.py` add
  `test_png_only_sheet_gets_docx_wrapper`: folder with only `eee_analysis.png`;
  assert a `eee_analysis.docx` is produced, is zip-openable and XML-parseable,
  `docx_wrapped=True`.
- [X] T027 [P] In `tests/test_normalise_analysis_sheets.py` add
  `test_reverse_wrap_is_idempotent`: a folder already having both `.png` and
  `.docx` → no re-wrap, mtime preserved, byte-identical `.docx` across two runs
  (determinism, research R9).

### Implementation

- [X] T028 In `normalise_analysis_sheets.py`, implement `wrap_png_in_docx(png:
  Path, docx_out: Path) -> bool` reusing the `mock_pptx.py:emit_docx` pattern
  (stdlib `zipfile` + `xml.etree`, **fixed `date_time=(1980,1,1,0,0,0)`** on each
  `ZipInfo`) to embed the PNG full-page. Return `False` on filesystem error.
  NEVER raises. (FR-018, research R9)
- [X] T029 In `normalise_analysis_sheets.py` `main`, for an analysis sheet that
  has a `.png` but no same-stem `.docx`, call `wrap_png_in_docx` (skip when the
  `.docx` already exists), recording `docx_wrapped` in the result and summary.

**Checkpoint**: both forms guaranteed for every analysis sheet; reverse wrap is
deterministic and idempotent.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T030 [P] Update `tests/test_run_pipeline_bat.py`
  (`test_batch_file_invokes_extract_then_generate`) to assert the new stage order
  `normalise → extract → pause → generate` (a `normalise_analysis_sheets.py`
  index before `extract_to_csv.py`) and an `errorlevel` guard on the normalise
  stage. (Breaks today without this update.)
- [X] T031 [P] Update `tests/test_mock_pptx.py`
  (`test_analysis_sheet_mix_includes_both_docx_and_png`) to assert the 3-way
  `{doc, docx, png}` mix from T013 (the old `docx/(docx+png)` ratio check fails
  once `doc` is added).
- [X] T032 [P] In `README.md`, add a "Renderer prerequisites" section:
  LibreOffice headless acquisition / install on the dev VM + air-gapped PC /
  air-gap transfer / `--renderer-cmd` override; the **optional** Pillow prep-time
  wheel for trim/DPI (FR-017) with its graceful-fallback note; both not-bundled /
  not-runtime-dependencies; and the single-landscape-page / first-page-with-warning
  behaviour. (FR-013, FR-017, Principle VI)
- [X] T033 [P] In `specs/001-pptx-dita-migration/contracts/csv-schema.md`, clarify
  (no column change) that for analysis rows whose source is `.doc`/`.docx`,
  `png_path` carries the rendered sibling `.png` from `normalise_analysis_sheets.py`
  (feature 007), and that FR-023's `analysis_docx_path` column was never
  implemented and is not introduced.
- [X] T034 [P] In `specs/001-pptx-dita-migration/contracts/cli-contracts.md`, add a
  `normalise_analysis_sheets.py` stanza mirroring
  `specs/007-analysis-sheet-images/contracts/normalise-cli.md`.
- [X] T035 Run `python -m unittest discover tests/` and confirm the whole suite is
  green (new module + extended `test_extract_to_csv.py` + updated
  `test_run_pipeline_bat.py` / `test_mock_pptx.py`), with and without Pillow
  installed.
- [X] T036 Execute `specs/007-analysis-sheet-images/quickstart.md` end-to-end
  against the mock corpus; confirm SC-001…SC-006 (inline image, both forms,
  byte-identical re-run, failures visible) and idempotency (second normalise run
  writes nothing).

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)** block everything.
- **Phase 3 (US1+US2, P1 MVP)** depends on Phase 2. This is the minimum shippable
  increment.
- **Phase 4 (US3, P2)** depends on Phase 3 (extends the same `main`/render paths
  and the extractor redirect).
- **Phase 5 (FR-017)** and **Phase 6 (FR-018)** depend on Phase 3 and are
  **independent of each other** — can be built in either order or in parallel.
- **Phase 7 (Polish)** depends on the phases whose behaviour it documents/verifies;
  T030/T031 depend on T014/T013 respectively; T035/T036 are last.

## Parallel Opportunities

- Phase 1: T002 ∥ T001 (after the skeleton lands, the stub is independent).
- Phase 3 tests: T005, T006, T007, T008, T009 are all `[P]` (distinct test
  functions / files). T013 (`mock_pptx.py`) ∥ T012 (`extract_to_csv.py`).
- Phase 4 tests: T015, T016, T017 `[P]`.
- Phases 5 & 6 can proceed concurrently after Phase 3.
- Phase 7: T030, T031, T032, T033, T034 are all `[P]` (distinct files).

## Implementation Strategy

- **MVP = Phases 1–3** (US1+US2): renders `.doc`/`.docx` to inline PNGs — the core
  value (no Word-launch delay). Shippable on its own.
- **Increment 2 = Phase 4** (US3): make failures visible and non-fatal — required
  for safe air-gapped operation.
- **Increment 3 = Phases 5–6** (FR-017/FR-018): image polish and the both-forms
  guarantee — the review-folded enhancements.
- **Finish = Phase 7**: regression-fix the two broken tests, document the
  prerequisites, sync the 001 contracts, run the suite + quickstart.

## Notes on invariants (carry through every phase)

- **One runtime dependency / stdlib-only tests**: the script's runtime path is
  stdlib; LibreOffice is stubbed (`--renderer-cmd`); Pillow is `skipUnless`. Never
  import Pillow at module top level.
- **Determinism**: rendered PNG and reverse `.docx` are committed source assets;
  the reverse wrap uses a fixed `date_time`; the normaliser is a no-op on an
  already-processed tree.
- **Warn-and-defer**: no renderer/Pillow/wrap failure aborts the run or raises;
  every failure is a WARNING surfaced in the log, summary, and CSV.

---

description: "Task list for PPTX to DITA Migration Pipeline"
---

# Tasks: PPTX to DITA Migration Pipeline

**Input**: Design documents from `/specs/001-pptx-dita-migration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required by FR-017 and User Story 5 (run on the air-gapped network with the standard library only). Test tasks are included in every user-story phase.

**Organization**: Tasks are grouped by user story. The MVP is User Story 1 (DITA generation from a signed-off CSV), since that produces the deliverable; subsequent stories add the upstream extraction, introspection, and tooling.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps task to a user story (US1–US6)
- File paths reflect the flat repository layout chosen in `plan.md`

## Path Conventions

Flat repository root:

- Scripts at root: `mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`, `generate_dita.py`, `run_pipeline.bat`, `README.md`, `requirements.txt`, `.gitignore`
- Tests under `tests/` with fixtures under `tests/fixtures/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repository scaffolding and the single dependency manifest. No source files yet; this phase only puts structural pieces in place.

- [X] T001 Create flat repository layout per plan.md §"Project Structure": empty placeholder files `mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`, `generate_dita.py`, `run_pipeline.bat`, `README.md`, plus `tests/` and `tests/fixtures/` directories at repository root
- [X] T002 [P] Create `requirements.txt` at repository root pinning `python-pptx` with `~=` compatibility (per research.md R12), and noting that no other runtime dependencies are required
- [X] T003 [P] Create `.gitignore` at repository root excluding `*.log`, `output/`, `tests/_tmp/`, `__pycache__/`, `*.pyc`, `mock_instructor.pptx`, `extracted.csv`, `wheels/`
- [X] T004 [P] Create `tests/__init__.py` (empty file, marks the test package for `unittest` discovery)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared test fixtures and the cross-cutting logging convention, both consumed by every user story.

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [X] T005 [P] Create `tests/fixtures/minimal.glc` — a minimal valid GLC XML document containing `data_source/filename`, `data_source/bitmap_crop_values/bottom_crop=271`, and `settings/lofar/bandwidth=400`, matching the example in `contracts/glc-schema.md`
- [X] T006 [P] Create `tests/fixtures/malformed.glc` — a GLC file truncated mid-tag so `xml.etree.ElementTree.parse` raises `ParseError` (used by parser tolerance tests per FR-005 and contracts/glc-schema.md)
- [X] T007 [P] Create `tests/fixtures/minimal.csv` — a 4-row CSV (one main GLC row with vessel name, one main analysis row, one progress-test GLC row, one WAV row with `wav_treatment=gaps-lite`) using the column structure in `contracts/csv-schema.md`; include UTF-8 BOM and CRLF line endings
- [X] T008 Document the dual stdout + per-stage-file logging convention from research.md R10 inside a top-of-file comment block in `generate_dita.py` (placeholder file from T001) so subsequent script tasks all reference the same convention; this becomes the in-repo reference for `setup_logging`

**Checkpoint**: Fixtures and the logging convention reference exist; user-story implementation can now begin.

---

## Phase 3: User Story 1 — Generate DITA Publications From Reviewed CSV (Priority: P1) 🎯 MVP

**Goal**: From a signed-off CSV, emit DITA topics, ditamaps, a manifest, and a skipped-rows report under a publication-and-chapter folder tree. This is the deliverable the project exists to produce.

**Independent Test**: Run `python generate_dita.py --csv tests/fixtures/minimal.csv --out tests/_tmp/output --image-root tests/fixtures` and verify the expected files exist, parse as well-formed XML, and contain the audience-filtered phrase wrapping `Nordik Jockey`.

### Tests for User Story 1

> **Write these tests FIRST and verify they fail before implementing the script.**

- [X] T009 [P] [US1] In `tests/test_generate_dita.py` add `test_glc_topic_structure` that runs the generator against `tests/fixtures/minimal.csv` and asserts the produced `gram_NN_lofarM.dita` parses as XML, contains a `<table outputclass="gram-config">`, has `time-end` and `freq-end` rows matching the CSV, and wraps the vessel name in `<ph audience="-trainee">` (FR-010, contracts/dita-topic-schema.md §1)
- [X] T010 [P] [US1] In `tests/test_generate_dita.py` add `test_analysis_topic_audience_attribute` asserting `gram_NN_analysis.dita` carries `audience="-trainee"` on the root topic element (FR-011, contracts/dita-topic-schema.md §2)
- [X] T011 [P] [US1] In `tests/test_generate_dita.py` add `test_main_ditamap_uses_topichead` asserting `ditamaps/main.ditamap` contains `<topichead navtitle="...">` with `<topicref>` children, in CSV row order (FR-012, contracts/dita-topic-schema.md §6.1)
- [X] T012 [P] [US1] In `tests/test_generate_dita.py` add `test_test_ditamap_is_flat` asserting `ditamaps/progress-test-1.ditamap` contains only `<topicref>` children of `<map>`, no `<topichead>` (FR-012, contracts/dita-topic-schema.md §6.2)
- [X] T013 [P] [US1] In `tests/test_generate_dita.py` add `test_wav_gaps_lite_stub` asserting that the row whose `wav_treatment=gaps-lite` produces a topic with the `<!-- MANUAL REVIEW -->` comment, a `<note>`, and an `<xref>` (FR-011 / R8 / contracts/dita-topic-schema.md §3)
- [X] T014 [P] [US1] In `tests/test_generate_dita.py` add `test_skipped_report_emitted_for_tbd_wav` asserting that a row with `wav_treatment=TBD` is *not* emitted as DITA, is logged at ERROR level, and appears in `skipped.txt` (FR-011, R8)
- [X] T015 [P] [US1] In `tests/test_generate_dita.py` add `test_idempotent_output` running the generator twice in a row against the same CSV and asserting that every produced file is byte-identical between runs (SC-004, FR-013, R9)
- [X] T016 [P] [US1] In `tests/test_generate_dita.py` add `test_manifest_lists_every_output_file` asserting `manifest.txt` exists at output root and lists every produced topic and ditamap, sorted, relative to `--out` (R9, contracts/dita-topic-schema.md §7)

### Implementation for User Story 1

- [X] T017 [US1] In `generate_dita.py`, scaffold `argparse` for `--csv`, `--out`, `--image-root` (all required), `--clean` (flag), wire `setup_logging` per the R10 convention writing to `generate.log` and stdout, and exit `1` on unhandled errors (contracts/cli-contracts.md §`generate_dita.py`)
- [X] T018 [US1] In `generate_dita.py`, implement `read_csv(path: Path) -> list[dict]` using `csv.DictReader` with `encoding="utf-8-sig"`, validating that the header matches `contracts/csv-schema.md` columns and raising a clear error if not (FR-014 no-silent-failure)
- [X] T019 [US1] In `generate_dita.py`, implement `slugify(text: str) -> str` for chapter directory names (lower-case, ASCII, hyphenated, collapsed runs) per research.md R3
- [X] T020 [US1] In `generate_dita.py`, implement `resolve_image_href(png_path: str, image_root: Path, topic_dir: Path) -> str` returning a path relative to `topic_dir` (contracts/dita-topic-schema.md §1 / §2)
- [X] T021 [US1] In `generate_dita.py`, implement `emit_glc_topic(row: dict, out_dir: Path, image_root: Path) -> Path` producing the gram-config DITA (contracts/dita-topic-schema.md §1); omit the `<ph audience="-trainee">` wrapper when `vessel_name` is empty (FR-010)
- [X] T022 [US1] In `generate_dita.py`, implement `emit_analysis_topic(row: dict, out_dir: Path, image_root: Path) -> Path` producing the analysis DITA with `audience="-trainee"` on the root (FR-011, contracts/dita-topic-schema.md §2)
- [X] T023 [US1] In `generate_dita.py`, implement `emit_wav_stub_topic(row: dict, out_dir: Path) -> Path` producing the GAPS-Lite stub topic with the manual-review XML comment (FR-011, R8, contracts/dita-topic-schema.md §3)
- [X] T024 [US1] In `generate_dita.py`, implement `dispatch_row(row: dict, out_dir: Path, image_root: Path) -> EmitResult` that branches on `topic_type` and `wav_treatment` per R8 (`screenshot` → glc emitter, `gaps-lite` → wav stub, `TBD`/empty/unknown → skip + ERROR log + skipped.txt entry)
- [X] T025 [US1] In `generate_dita.py`, implement `emit_main_ditamap(rows: list[dict], out_dir: Path) -> Path` writing `ditamaps/main.ditamap` with `<topichead>` per chapter and `<topicref>` children in CSV order (FR-012, contracts/dita-topic-schema.md §6.1)
- [X] T026 [US1] In `generate_dita.py`, implement `emit_test_ditamap(publication: str, rows: list[dict], out_dir: Path) -> Path` writing the flat `progress-test-N.ditamap` (FR-012, contracts/dita-topic-schema.md §6.2)
- [X] T027 [US1] In `generate_dita.py`, implement `write_manifest(out_dir: Path, files: list[Path]) -> None` writing `manifest.txt` (sorted, relative paths, LF line endings) per R9 / contracts/dita-topic-schema.md §7
- [X] T028 [US1] In `generate_dita.py`, implement `write_skipped_report(out_dir: Path, skipped: list[SkippedRow]) -> None` writing `skipped.txt` only when there is at least one skipped row, in CSV row order (R8, contracts/dita-topic-schema.md §5)
- [X] T029 [US1] In `generate_dita.py`, implement `main()` orchestration: clean output if `--clean` is set, group rows by publication, dispatch each row, emit ditamaps, write manifest and skipped report, log the end-of-run summary (topics generated, ditamaps generated, skipped, errors) per FR-014
- [X] T030 [US1] In `generate_dita.py`, ensure all file writes use `encoding="utf-8"`, no BOM, LF line endings (`newline="\n"`) per contracts/dita-topic-schema.md preamble; ensure determinism (sorted iteration, no timestamps in content) for SC-004 idempotency

**Checkpoint**: User Story 1 is fully functional — given a signed-off CSV, the generator produces the complete DITA output tree, manifest, and skipped report. Tests T009–T016 pass.

---

## Phase 4: User Story 2 — Extract PPTX Content Into a Reviewable CSV (Priority: P2)

**Goal**: Walk a content root, parse PPTXs and their GLC files, and emit the intermediate CSV with warnings inline, leaving the shape-grouping logic as a documented stub per FR-015.

**Independent Test**: Run `python extract_to_csv.py --input-root tests/fixtures/sample-content --out tests/_tmp/extracted.csv` and verify that the run reaches the (intentionally) raised `NotImplementedError` only after argparse, walk, logging setup, and routing have all succeeded; verify `parse_glc()` against `tests/fixtures/minimal.glc` and `tests/fixtures/malformed.glc` directly via the test suite.

### Tests for User Story 2

- [X] T031 [P] [US2] In `tests/test_glc_parser.py` add `test_parse_minimal_glc_returns_expected_fields` asserting `parse_glc(Path("tests/fixtures/minimal.glc"))` returns `time_end="271"`, `freq_end="400"`, `image_filename="gram12.PNG"`, and an empty warnings list (FR-005, contracts/glc-schema.md)
- [X] T032 [P] [US2] In `tests/test_glc_parser.py` add `test_parse_malformed_glc_returns_empty_with_warning` asserting the malformed fixture yields empty fields and a single warning starting with `"GLC malformed:"` (R6, contracts/glc-schema.md)
- [X] T033 [P] [US2] In `tests/test_glc_parser.py` add `test_parse_glc_strips_windows_path` constructing an in-memory GLC with `<filename>W:\foo\bar\file.PNG</filename>` and asserting `image_filename == "file.PNG"` (FR-005, R6)
- [X] T034 [P] [US2] In `tests/test_glc_parser.py` add `test_parse_glc_records_missing_element_warnings` asserting that GLCs missing `<bottom_crop>` / `<bandwidth>` / `<filename>` produce the verbatim warning strings listed in contracts/glc-schema.md
- [X] T035 [P] [US2] In `tests/test_extract_to_csv.py` add `test_argparse_and_logging_succeed_before_stub` running the script with mocked `extract_grams_from_slide` and asserting that walk, routing, GLC parse, and CSV write all run end-to-end (covers all infrastructure that FR-015 requires fully implemented)
- [X] T036 [P] [US2] In `tests/test_extract_to_csv.py` add `test_progress_test_routing` asserting that a PPTX whose name matches `--test-pattern` is routed to `publication=progress-test-N` with empty `chapter`, while a non-matching PPTX is routed to `publication=main` with chapter slugified from its parent folder (FR-002, R2, R3)
- [X] T037 [P] [US2] In `tests/test_extract_to_csv.py` add `test_missing_glc_records_warning_not_raises` asserting that an unresolved GLC reference produces a CSV row with empty measurements and `warnings` containing `"GLC not found"`, and the script exits 0 (FR-006, FR-014)
- [X] T038 [P] [US2] In `tests/test_extract_to_csv.py` add `test_csv_round_trip_invariant` writing rows with the writer, reading them back with `csv.DictReader(encoding="utf-8-sig")`, and asserting equality (R11, contracts/csv-schema.md round-trip section)

### Implementation for User Story 2

- [X] T039 [US2] In `extract_to_csv.py`, scaffold `argparse` for `--input-root`, `--out` (both required), `--test-pattern` (default `progress_test`); wire `setup_logging` to `extract.log` and stdout per R10 (contracts/cli-contracts.md §`extract_to_csv.py`)
- [X] T040 [US2] In `extract_to_csv.py`, implement `parse_glc(path: Path) -> GlcDocument` honouring contracts/glc-schema.md exactly: tolerant XML parse, `pathlib.PureWindowsPath(raw).name` for the filename, verbatim warning strings, never raises (FR-005, R6)
- [X] T041 [US2] In `extract_to_csv.py`, implement `resolve_glc_path(href: str, content_root: Path) -> Path | None` handling both per-gram and per-ten-grams supporting layouts (FR-006); return `None` and log a WARNING when not found
- [X] T042 [US2] In `extract_to_csv.py`, implement `walk_pptxs(input_root: Path) -> Iterator[Path]` yielding every `.pptx` under the root, sorted for deterministic output (R2)
- [X] T043 [US2] In `extract_to_csv.py`, implement `classify_publication(pptx: Path, test_pattern: str, allocated: dict) -> tuple[str, str | None, str | None]` returning `(publication, chapter, chapter_slug)` per R2/R3, allocating progress-test numbers in stable filename order
- [X] T044 [US2] In `extract_to_csv.py`, implement `extract_grams_from_slide(slide, slide_num: int) -> list[GramPlaceholder]` as the documented `NotImplementedError` stub specified in FR-015 / spec.md §5.3, with a docstring listing the five introspection questions verbatim from the source spec *(stub now superseded — see T104 in Phase 10, which replaces it using the grouping rule documented in `source/notes/reverse-spec.md` §4)*
- [X] T045 [US2] In `extract_to_csv.py`, implement `gram_to_rows(gram: GramPlaceholder, publication: str, chapter: str, content_dir: Path) -> list[dict]` producing one CSV row per GLC link (numbered by sequence) plus one analysis row, populating `warnings` from each `parse_glc` and `resolve_glc_path` call (FR-003, FR-004, contracts/csv-schema.md §"Row construction rules")
- [X] T046 [US2] In `extract_to_csv.py`, implement `write_csv(rows: list[dict], out: Path) -> None` using `csv.DictWriter` with `encoding="utf-8-sig"`, `lineterminator="\r\n"`, `quoting=csv.QUOTE_MINIMAL`, and the column order from contracts/csv-schema.md (R11)
- [X] T047 [US2] In `extract_to_csv.py`, implement `main()` orchestration: walk PPTXs, classify each, open each via `python-pptx`, iterate slides, call the (stubbed) grouping function, expand to rows, write CSV, emit end-of-run summary (total PPTXs, total rows, total warnings, distinct warning types) per FR-014

**Checkpoint**: User Story 2's infrastructure is complete and tested. Shape grouping remains the loud, documented stub from FR-015. Once introspection has been run against a real instructor presentation, the stub is replaced — but that is out of scope here.

---

## Phase 5: User Story 3 — Introspect a PPTX to Confirm Structural Assumptions (Priority: P3)

**Goal**: Produce a structural report covering hyperlink mechanisms, shape inventory, and per-slide layout so the team can confirm assumptions and unblock the shape-grouping stub.

**Independent Test**: Run `python introspect_pptx.py --input mock_instructor.pptx --out tests/_tmp/report.txt` against a freshly generated mock PPTX and verify the summary counts match the mock's known structure.

### Tests for User Story 3

- [X] T048 [P] [US3] In `tests/test_introspect.py` add `test_summary_counts_match_mock_structure` running the script against a mock PPTX produced via `setUpClass` and asserting that slide count, `.glc`/`.png`/`.wav` extension counts, and shape-level vs text-run hyperlink counts match the constants exported by `mock_pptx.py` (FR-007)
- [X] T049 [P] [US3] In `tests/test_introspect.py` add `test_per_slide_section_records_position_and_text` asserting each shape's index, name, type, position in inches (2dp), truncated text, and hyperlinks at both shape and run level appear in section 2 (FR-007, FR-008)
- [X] T050 [P] [US3] In `tests/test_introspect.py` add `test_hyperlink_targets_section_groups_by_extension` asserting section 3 lists every distinct hyperlink target deduplicated and grouped by file extension (FR-007)
- [X] T051 [P] [US3] In `tests/test_introspect.py` add `test_slides_filter_restricts_per_slide_section` running with `--slides 2` and asserting only slide 2 appears in section 2, while sections 1 and 3 still report on the whole deck (contracts/cli-contracts.md §`introspect_pptx.py`)
- [X] T052 [P] [US3] In `tests/test_introspect.py` add `test_unexpected_shape_count_is_flagged` constructing or doctoring a mock with too few shapes on one slide and asserting that slide is flagged in section 1 (FR-007)

### Implementation for User Story 3

- [X] T053 [US3] In `introspect_pptx.py`, scaffold `argparse` for `--input` (required), `--out` (optional, defaults to stdout), `--slides` (comma-separated ints); wire `setup_logging` to `introspect.log` and stdout per R10
- [X] T054 [US3] In `introspect_pptx.py`, implement `extract_run_hyperlink(run) -> tuple[str | None, str]` returning `(target, "text-run")` or `(None, "")` per the XML access pattern in R4 / spec.md §4.5; never raises
- [X] T055 [US3] In `introspect_pptx.py`, implement `extract_shape_hyperlink(shape) -> tuple[str | None, str]` returning `(target, "shape-level")` or `(None, "")` per R4 / spec.md §4.5; never raises
- [X] T056 [US3] In `introspect_pptx.py`, implement `collect_shape_records(slide) -> list[ShapeRecord]` walking shapes (expanding GROUPs), recording position in inches (rounded 2dp), text, and both hyperlink types
- [X] T057 [US3] In `introspect_pptx.py`, implement `render_summary(records: list[ShapeRecord], total_slides: int, expected_per_slide: int) -> str` producing section 1 (filename, slide count, hyperlink target extensions with counts, shape-level vs text-run counts, deviating-slide list) per FR-007
- [X] T058 [US3] In `introspect_pptx.py`, implement `render_per_slide(records: list[ShapeRecord], slides_filter: list[int] | None) -> str` producing section 2 (per-slide, per-shape index/name/type/position/truncated-text/hyperlinks) per FR-007
- [X] T059 [US3] In `introspect_pptx.py`, implement `render_hyperlinks(records: list[ShapeRecord]) -> str` producing section 3 (deduplicated targets grouped by extension, with hyperlink type, slide number, shape name) per FR-007
- [X] T060 [US3] In `introspect_pptx.py`, implement `main()` orchestration: open the PPTX, collect records across slides, render the three sections concatenated, write to `--out` (UTF-8) or stdout

**Checkpoint**: User Story 3 is fully functional — running introspection against the mock or a real PPTX produces the structural report needed to unblock the FR-015 stub.

---

## Phase 6: User Story 4 — Generate a Realistic Mock PPTX for Testing (Priority: P4)

> **Note (post-reverse-spec):** This phase was completed against the pre-reverse-spec model (one fixed-shape PPTX, 3×5 grid, 15 grams per slide, welcome slide, hand-picked vessel pool). The corpus-aware redesign that matches `source/notes/reverse-spec.md` lives in **Phase 10 (T093–T103)** and supersedes the implementation parts of this phase. The tests and constants below remain a useful historical record.

**Goal**: Produce a synthetic instructor PPTX that exercises every structural case in the source spec — used by the introspection and extraction test suites and as a teaching tool for the air-gapped maintainer.

**Independent Test**: Run `python mock_pptx.py --out tests/_tmp/mock.pptx` and inspect with `introspect_pptx.py`; alternately run the unit tests in `tests/test_mock_pptx.py`.

### Tests for User Story 4

- [X] T061 [P] [US4] In `tests/test_mock_pptx.py` add `test_slide_count` asserting the generated PPTX has the expected total slide count (1 welcome + N content) per spec.md §3.2
- [X] T062 [P] [US4] In `tests/test_mock_pptx.py` add `test_each_content_slide_has_15_grams` asserting every content slide contains exactly 15 title rectangles and 15 link text boxes (FR-009, spec.md §3.2)
- [X] T063 [P] [US4] In `tests/test_mock_pptx.py` add `test_title_shapes_have_shape_level_hyperlinks` asserting every title rectangle carries a shape-level click action targeting an `analysis.png` file (FR-009)
- [X] T064 [P] [US4] In `tests/test_mock_pptx.py` add `test_link_boxes_have_text_run_hyperlinks` asserting every link text box carries text-run hyperlinks ending in `.glc` or `.wav` (FR-009)
- [X] T065 [P] [US4] In `tests/test_mock_pptx.py` add `test_wav_grams_have_wav_link` asserting the configured WAV-override grams (5 and 20 per spec.md §3.2) carry a `.wav` link

### Implementation for User Story 4

- [X] T066 [US4] In `mock_pptx.py`, define module-level constants per R5: `VESSEL_NAMES` (≥30 entries from the realistic pool in spec.md §3.2), `LINK_COUNT_BY_GRAM_RANGE` mapping the (1–10, 11–25, 26–30) variation tiers, `WAV_GRAMS = (5, 20)`, slide dimensions (13.33" × 7.5"), grid geometry (3 rows × 5 cols, ~1" top margin)
- [X] T067 [US4] In `mock_pptx.py`, scaffold `argparse` for `--out` (required) and a top-level `if __name__ == "__main__":` block; use `print()` for progress per FR-014's exception for the mock generator
- [X] T068 [US4] In `mock_pptx.py`, implement `add_welcome_slide(prs)` — title `"Welcome to AAAC Training Module 3"`, subtitle `"Instructor Version"` (spec.md §3.2)
- [X] T069 [US4] In `mock_pptx.py`, implement `add_shape_level_hyperlink(shape, target: str)` performing the direct lxml manipulation under `p:nvSpPr/p:nvPr/a:hlinkClick` and registering the relationship via `shape.part.relate_to` (R5, spec.md §4.5)
- [X] T070 [US4] In `mock_pptx.py`, implement `add_text_run_hyperlink(run, target: str)` using python-pptx's relationship API to attach `a:hlinkClick` to the run's `a:rPr` (R5)
- [X] T071 [US4] In `mock_pptx.py`, implement `build_gram_placeholder(slide, row: int, col: int, gram_num: int, vessel: str, link_count: int, is_wav: bool)` producing the title rectangle (with shape-level hyperlink to `../images/gramNN_analysis.png`) and the link text box (with text-run hyperlinks to `../gramNN/config_M.glc` or `.wav`) per spec.md §3.2
- [X] T072 [US4] In `mock_pptx.py`, implement `add_content_slide(prs, slide_num: int, gram_start: int, gram_end: int)` placing 15 placeholders in a 3×5 grid via `build_gram_placeholder`
- [X] T073 [US4] In `mock_pptx.py`, implement `main()` orchestration: build the presentation, add the welcome slide, add content slides covering grams 1–30, save to `--out`, print a progress summary

**Checkpoint**: User Story 4 is fully functional — the mock generator produces a PPTX that the test suite for User Stories 3 and 5 can rely on.

---

## Phase 7: User Story 5 — Run the Test Suite on the Air-Gapped Network (Priority: P5)

**Goal**: Ensure that the entire test suite is discoverable and runnable with the standard library only, on the air-gapped network without internet or AI assistance, with a clear failure surface that points at the affected script.

**Independent Test**: From a clean checkout, run `python -m unittest discover tests/` and verify all tests run under one minute and report green; deliberately break a function in any script and verify the corresponding test fails with a message that names the file under test.

### Tests for User Story 5

- [X] T074 [P] [US5] In `tests/test_air_gapped_readiness.py` add `test_no_third_party_imports_other_than_pptx` parsing each `.py` file under tests and the script roots and asserting that the only third-party import name encountered is `pptx` (FR-017, plan.md §"Constraints")
- [X] T075 [P] [US5] In `tests/test_air_gapped_readiness.py` add `test_test_suite_runs_under_one_minute` running `unittest.main(exit=False, verbosity=0)` on the discovered suite under a `time.perf_counter()` budget and asserting the total elapsed is below 60 s on a standard workstation (SC-003)
- [X] T076 [P] [US5] In `tests/test_air_gapped_readiness.py` add `test_every_script_has_corresponding_test_module` asserting that for every script in `mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`, `generate_dita.py`, a `tests/test_<script>.py` file exists (FR-017)

### Implementation for User Story 5

- [X] T077 [US5] In `tests/__init__.py` (initially empty from T004), document the discovery command and the `tests/_tmp/` convention for ephemeral fixtures, plus the rule that no fixture larger than 50 KB is committed (R13)
- [X] T078 [US5] In `tests/conftest_helpers.py` (a regular module, not a pytest conftest), implement `make_mock_pptx(tmp_path: Path) -> Path` that invokes `mock_pptx.main` with `--out tmp_path/mock.pptx` and returns the path; reused by US3 and US5 tests via `setUpClass` to avoid committing a binary fixture (R13) *(signature and return shape change in T102 — corpus mode returns the root directory; callers must pick a specific PPTX from a family)*
- [X] T079 [US5] Add a `test:` entry to `README.md` (created in Phase 1 / extended in T084) documenting the exact discovery command, expected runtime, and what to do when a test fails on the air-gapped network (FR-018 §8 "Running tests")

**Checkpoint**: User Story 5 is fully functional — the air-gapped maintainer can run, read, and triage every test without internet or AI access.

---

## Phase 8: User Story 6 — Run the End-to-End Pipeline From a Single Command (Priority: P6)

**Goal**: Provide a Windows batch wrapper that runs Stage 2 → operator review → Stage 4 with proper exit-code propagation.

**Independent Test**: On a Windows host (or via a manual review), invoke `run_pipeline.bat path-to-content` and verify that extraction runs, the operator is paused for CSV review, generation runs after `pause` returns, and the wrapper exits non-zero if either Python stage fails.

### Tests for User Story 6

- [X] T080 [P] [US6] In `tests/test_run_pipeline_bat.py` add `test_batch_file_invokes_extract_then_generate` parsing `run_pipeline.bat` as text and asserting the call order is `extract_to_csv.py` → `pause` → `generate_dita.py`, with `if errorlevel 1 goto error` after each Python invocation (contracts/cli-contracts.md §`run_pipeline.bat`)
- [X] T081 [P] [US6] In `tests/test_run_pipeline_bat.py` add `test_batch_forwards_input_root_argument` asserting the wrapper passes `%1` to both `--input-root` (extractor) and `--image-root` (generator)

### Implementation for User Story 6

- [X] T082 [US6] Author `run_pipeline.bat` per spec.md §7 and contracts/cli-contracts.md §`run_pipeline.bat`: stage banners, `extract_to_csv.py --input-root %1 --out extracted.csv` with `if errorlevel 1 goto error`, `pause > nul`, `generate_dita.py --csv extracted.csv --out output\ --image-root %1` with `if errorlevel 1 goto error`, `:error` block exiting with code 1, `:end` block exiting cleanly

**Checkpoint**: User Story 6 is fully functional — the batch wrapper runs the end-to-end pipeline with proper review pause and exit-code propagation.

---

## Phase 9: Polish & Cross-Cutting Concerns

> **Note (post-reverse-spec):** Phase 9 produced the README before FR-021 was added. The new "Publishing to HTML (optional)" section lives in **Phase 10 (T106)**.

**Purpose**: Documentation completion, air-gapped install hardening, and final validation against the quickstart.

- [X] T083 [P] In `README.md`, add the *Project context* section summarising what the pipeline does and why, sourced from spec.md §1.1 and plan.md §Summary (FR-018 §1)
- [X] T084 [P] In `README.md`, add the *Prerequisites* section with the Python 3.11+ requirement, the development-VM `pip install python-pptx` route, and the air-gapped wheelhouse procedure from research.md R12 (FR-018 §2)
- [X] T085 [P] In `README.md`, add the *Folder structure* section describing the role of each script (FR-018 §3)
- [X] T086 [P] In `README.md`, add the *Quickstart* section paraphrasing `specs/001-pptx-dita-migration/quickstart.md` for the project root (FR-018 §4)
- [X] T087 [P] In `README.md`, add the *Stage-by-stage guide* including what the technical author should look for during CSV review (FR-018 §5)
- [X] T088 [P] In `README.md`, add the *CSV column reference* section, copying the table from contracts/csv-schema.md and adapting it for end-user prose (FR-018 §6)
- [X] T089 [P] In `README.md`, add the *Troubleshooting* section listing common warnings and resolutions, sourced from quickstart.md "Troubleshooting smoke tests" plus contracts/glc-schema.md warning vocabulary (FR-018 §7)
- [X] T090 [P] In `README.md`, add the *Known limitations* section explicitly calling out the FR-015 shape-grouping stub, the WAV `TBD` skip behaviour, and the no-cleanup default for `output/` (FR-018 §9)
- [ ] T091 Run the quickstart end-to-end on the development VM exactly as written in `specs/001-pptx-dita-migration/quickstart.md`, recording any drift between the documented commands and the actual scripts; fix any discrepancies and re-run until quickstart and reality agree *(manual; defer to development VM)*
- [ ] T092 Verify SC-005 manually on the development VM: run an Oxygen build of the generated DITA tree against both an instructor profile (no audience exclusion) and a trainee profile (excluding `-trainee`); record any build failures and resolve *(manual; defer to development VM)*

---

## Phase 10: Reverse-Spec Adaptation & DITA-OT Documentation

**Purpose**: Re-align the mock generator, the FR-015 stub, and the README with two post-Phase-9 inputs: (a) `source/notes/reverse-spec.md`, which describes the real source corpus shape that earlier phases could only guess at (multi-publication corpus across three families, descriptor-split-at-colon, rounded-rect + Lofar-labels gram tile, hyperlink mechanism, Pub10_Ed22B batched folders, etc.); and (b) FR-021, which adds a DITA-OT + Java HTML-preview path documented in the README but not bundled in the delivery.

**Amendment (2026-05-15):** The generated corpus is committed under `source/<publication>/` as a deliverable artifact (overrides R13's "no binary fixtures > 50 KB" rule for this dataset specifically). Rationale: a reviewable, regeneratable corpus on the air-gapped network is more valuable than a small repo; the generator (`mock_pptx.py`) plus a fixed RNG seed keep the corpus reproducible from source. `source/notes/` retains its prior role; new top-level publication folders sit alongside it.

**Inputs**: [`source/notes/reverse-spec.md`](../../source/notes/reverse-spec.md) (corpus shape), spec.md FR-021 (DITA-OT documentation requirement), plan.md "External Toolchain" note.

**Why this phase exists**: Phases 6 (mock generator) and 4 (FR-015 stub) were written before the reverse-spec interview, so the mock produced one fixed-shape PPTX and the shape-grouping logic was a documented `NotImplementedError`. The reverse-spec now supplies both the corpus shape (so the mock can be corpus-aware) and the grouping rule (so the stub can be implemented). Phase 9 produced the README before FR-021 was added, so the DITA-OT section is missing.

### Mock generator redesign (supersedes parts of Phase 6)

- [X] T093 [US4] Redesign `mock_pptx.py` for the multi-publication corpus per `source/notes/reverse-spec.md` §1, §3, §4: produce ~11 publication folders across three families (Weeks ×4, Progress Tests ×5 including a "No FR" variant, Final Assessment ×1, Pub10_Ed22B ×1), each with its own `<Name>.pptx` plus a sibling `<Name> Files/` folder of `Gram N/` subfolders. Drop the welcome slide. Replace the fixed 3×5 / 15-gram-per-slide model with per-family parameters (reverse-spec §7).
- [X] T094 [US4] Adapt `mock_pptx.py`'s CLI from `--out <file>` to `--out-root <dir>` (corpus output); supersede T067's single-file CLI. Document the new CLI in `contracts/cli-contracts.md` §`mock_pptx.py`.
- [X] T095 [US4] In `mock_pptx.py`, build a Star Trek + Star Wars vocabulary (vessel classes, ship names, codenames) per reverse-spec §6, with deterministic 2–6 cross-publication repeats. Replace the existing `VESSEL_NAMES` constant. Keep generation deterministic via a fixed RNG seed for SC-004-style reproducibility.
- [X] T096 [US4] In `mock_pptx.py`, implement the gram-tile shape per reverse-spec §4: a rounded rectangle whose text follows `"Gram N: <descriptor>"` (descriptor synthesised from the vessel pool with deliberate format variance — sometimes `"FR <vessel>, Category <K>, <codename>"`, sometimes a free-form sentence) and a shape-level hyperlink to a `Gram N/Analysis Sheet.docx` or `Gram N/Analysis.png` (50/50 mix per reverse-spec §7); plus 1–4 text labels labelled `"Lofar 1"`…`"Lofar N"` (uniform random count) each carrying a text-run hyperlink to a distinct `Gram N/<name>.glc` in the same gram folder.
- [X] T097 [US4] In `mock_pptx.py`, implement gram-number gap generation (reverse-spec §7): for each publication, draw the target gram count from the family parameter, then drop a small random subset of integers from the sequence to simulate edit history (e.g. retain 32 of 35 numbers for a Weeks deck), so the resulting sequence is non-contiguous but the surviving grams keep their original numbers.
- [X] T098 [US4] In `mock_pptx.py`, implement the Pub10_Ed22B `Files/` folder batching per reverse-spec §2: split that publication's gram subfolders into ten-gram parents (`Pub 10_Ed 2_(1-10)`, `(11-20)`, …), keep slides at ~15 grams each, and ensure PPTX hyperlinks span batch folders. Other publications retain a flat `Files/` layout.
- [X] T099 [US4] In `mock_pptx.py`, implement asset emission for each gram via the standard library only: write the `.glc` as `GAPS_Lite_configuration` XML per `contracts/glc-schema.md`; write a small valid `.png` using a pre-computed byte template (no PIL); write a short silence `.wav` via the stdlib `wave` module; write a minimal valid `.docx` using `zipfile` + `xml.etree` (no `python-docx`). Mostly PNG-referencing GLCs with a minority of WAV-referencing GLCs per reverse-spec §7.
- [X] T100 [US4] In `mock_pptx.py`, implement title-bar emission per reverse-spec §3: each slide's title bar uses `"<Publication> — Page N of M"` format, with a generic placeholder logo (text-in-a-coloured-box; no real org imagery). No speaker notes.

### Mock test updates (supersedes parts of Phase 6)

- [X] T101 [P] [US4] Update `tests/test_mock_pptx.py` to assert against the corpus-aware model: a single run produces a directory tree with one PPTX per publication, family-appropriate gram counts (±5%), variable Lofar counts (1–4), 50/50 analysis-sheet mix, the Pub10_Ed22B batched folder layout, and deterministic regeneration (two runs byte-identical given the same seed). Drop T061–T065's assumptions about a single PPTX with 15 grams per slide.
- [X] T102 [P] [US4] Update `tests/conftest_helpers.py::make_mock_pptx` (originally T078) for the new CLI and the new return type: now returns the corpus root path (a directory), and callers that need a single PPTX pick a specific one by family (e.g. the first Week). Update US3 and US5 callers accordingly.
- [X] T103 [P] [US4] In `tests/test_mock_pptx.py`, add `test_gram_tile_uses_descriptor_colon_split` asserting that every gram rectangle's text matches `r"^Gram \d+: "` so the student/instructor split at the first colon is well-defined (reverse-spec §4).

### Replace FR-015 stub (task only; implementation deferred per current scope)

- [X] T104 [US2] Replace the `NotImplementedError` body of `extract_grams_from_slide(slide, slide_num)` in `extract_to_csv.py` with the documented grouping rule from `source/notes/reverse-spec.md` §4: locate each rounded-rectangle shape carrying a shape-level hyperlink (treat as the gram header — descriptor split at the first colon yields `gram_id` and instructor-visible detail; href is the analysis-sheet path), then for each rectangle find the text-frame shape(s) immediately beneath it that contain runs hyperlinked to `.glc` files (one Lofar each). Return a list of `GramPlaceholder` records. Update T044's docstring-only stub accordingly.
- [X] T105 [US2] Update `tests/test_extract_to_csv.py`: remove `test_argparse_and_logging_succeed_before_stub` (T035) since the stub is gone, and add tests for the grouping rule using a mock PPTX from `make_mock_pptx` — assert that the row count for a known mock publication matches the expected number of GLC links plus one analysis row per gram, and that descriptor split at the colon populates `gram_id` and a separate instructor-visible field on the row.

### DITA-OT documentation (new — supersedes nothing)

- [ ] T106 [P] In `README.md`, add a `Publishing to HTML (optional)` section per FR-021: (a) acquisition of DITA-OT and a Java runtime (with version compatibility note), (b) Windows install steps on the air-gapped target including how the maintainer transfers the installers across the air-gap, (c) the exact DITA-OT command line for rendering `output/main/main.ditamap` and each `output/progress-test-N/...ditamap` to HTML, (d) explicit caveats that DITA-OT is for sanity-checking only, that Oxygen XML Author is the production publishing path, and that DITA-OT and Java are not bundled in the project delivery.

### Plan / spec alignment

- [ ] T107 Cross-check `plan.md` and `spec.md` after T093–T106 land: ensure the "Project Structure" section still matches the actual file layout, that no assumption in `spec.md` §Assumptions has been contradicted by the new mock-corpus shape (especially the "Each content slide hosts exactly 15 gram placeholders in a 3×5 grid" assumption — now superseded by reverse-spec §3), and amend or remove that assumption with a pointer to the reverse-spec.

## Phase 11: Self-Contained Publication Tree (FR-022) & HTML Publish Helper

**Purpose**: Re-running the DITA pipeline (after CSV changes upstream) should produce a self-contained `dita/` tree with assets copied next to their owning topics, and a one-command HTML preview path. Captures the work that produced the committed `dita/` and `html/` snapshots on branch `claude/write-dita-docs-n7uFB` so that a future regeneration follows the same recipe.

**Inputs**: FR-022 (asset copy and rename), updated `contracts/dita-topic-schema.md` §10–11, the existing `generate_dita.py` skeleton from Phase 3.

### Asset copy in the DITA generator (FR-022)

- [X] T108 [US1] In `generate_dita.py`, add a `copy_asset(src_relpath, image_root, topic_dir, topic_stem)` helper that resolves the source asset, copies it next to the topic (`shutil.copy2` to preserve mtime for idempotency), renames the copy to `{topic_stem}{ext}`, and returns `(href, written_path)`. When the source is missing, log a WARNING and return the intended local filename anyway so the topic XML is stable across runs.
- [X] T109 [US1] Wire `copy_asset` into `emit_glc_topic`, `emit_analysis_topic`, and `emit_wav_stub_topic`. Each emit function now returns `list[Path]` (topic + optionally the copied asset). The WAV stub uses `link_href` (then `glc_path` fallback) as the source and emits `scope="local"` on the `<xref>` to reflect the in-publication location of the renamed WAV.
- [X] T110 [US1] Update `dispatch_row` to return `(list[Path], dict | None)` and the main loop to iterate the list when accumulating `written`. Adjust the summary log line from `topics=N` to `files=N` to reflect the union of topics and assets.
- [X] T111 [US1] In `tests/test_generate_dita.py`, add `test_glc_topic_asset_copied_with_relative_href`: drop a real 1×1 PNG fixture at `tests/fixtures/images/gram12.png`, run the generator, and assert that (a) the copy lands at `<chapter>/gram_12_lofar1.png` with byte-identical content, and (b) the topic's `<image href>` is the bare local filename. Update `test_wav_gaps_lite_stub` to assert the new local-href shape (`gram_05_lofar1.wav`).
- [X] T112 [US1] Update the `image_href` substitution row in `contracts/dita-topic-schema.md` §1; rewrite the WAV-stub paragraph in §3 (now `scope="local"` plus a local filename); extend the §9 folder-layout sketch to show assets sitting alongside topics; add new §10 codifying the asset copy/rename contract.

### HTML publish helper (FR-021)

- [X] T113 Add `publish_html.py` at the repository root: stage a copy of `dita/` to `.dita-build/`, inject DITA Topic and Map DOCTYPEs into the staged files (the source DITA tree omits them per §0 — Oxygen handles validation), promote each ditamap to the staged root with `href="../…"` rewritten to drop the leading `../`, and invoke DITA-OT (`bin/dita --format=html5 --processing-mode=lax`) once per staged ditamap, writing to `html/<ditamap-stem>/`. Clean the staging directory once publishing completes. The script is standard-library-only; DITA-OT is supplied via `--dita-ot`.
- [X] T114 In `.gitignore`, add `.dita-build/` (the staging directory must never be committed).
- [X] T115 Add new §11 to `contracts/dita-topic-schema.md` documenting the staging/promotion/invocation recipe so a future maintainer can reproduce or audit `publish_html.py` without reading its source.

### Spec / plan / quickstart alignment

- [X] T116 In `spec.md`, append FR-022 (self-contained publication tree, asset copy/rename, dangling-href stability) and extend FR-021 to mention the `publish_html.py` helper. Update FR-010's "image reference" wording from "resolved against the image root" to "topic-relative local filename — see FR-022".
- [X] T117 In `plan.md`, add `publish_html.py` to the *Source Code (repository root)* listing; update the *Storage* line to mention copied assets and the `html/` preview output.
- [X] T118 In `quickstart.md`, change the §6 example to `--out dita/`; add the asset-copy expectations to the list of generator outputs; add new §9 covering `publish_html.py`; renumber the orchestrator step to §10.
- [X] T119 In `run_pipeline.bat`, change the default output path from `output\` to `dita\` to match the operator-facing convention. README example updated to match.

**Checkpoint**: After Phase 11, `generate_dita.py` emits self-contained publication trees (assets copied next to topics with stable local hrefs) and `publish_html.py` renders the trees to HTML via DITA-OT. The Phase 10 checkpoint above still applies: mock generator is corpus-aware, the FR-015 stub is replaced, README documents DITA-OT preview, and the spec/plan/reverse-spec are coherent. T091 and T092 (manual VM validation) remain the only outstanding tasks from Phase 9.

---

## Phase 12: Analysis-Sheet Normalisation (FR-023)

**Purpose**: Add the per-gram-folder normalisation stage that guarantees both `Analysis Sheet.docx` and `Analysis.png` exist for every gram folder before extraction emits an analysis CSV row. Runs *once per gram folder*, not per CSV row and not per gram instance on a slide. The stage is upstream of FR-022's asset copy: by the time `generate_dita.py` copies `Analysis.png` next to its topic, FR-023 has guaranteed the PNG exists.

**Inputs**: spec.md FR-023 + the new analysis-sheet edge case + the new renderer assumption; data-model.md §1.7 `AnalysisSheet`; the new `analysis_docx_path` column in contracts/csv-schema.md.

**Why this phase exists**: Real gram folders carry the analysis as either `Analysis Sheet.docx` *or* `Analysis.png` (roughly 50/50 per reverse-spec §7). The DITA generator's asset copy (FR-022 / Phase 11) assumes the PNG already exists in the gram folder; the technical author and downstream artefact consumers depend on the `.docx` also being present. The mock generator (T096) already emits the 50/50 mix; the normalisation stage is the inverse pipeline step that makes them interchangeable for downstream consumers.

### CLI + contract

- [ ] T120 In `contracts/cli-contracts.md`, add a `normalise_analysis_sheets.py` section: `--content-root` (required), `--renderer-cmd` (optional, defaults to `soffice` for LibreOffice headless), `--dry-run` (flag — log what would happen without modifying disk). Document exit codes: `0` on success including renderer-failure-with-warnings, `1` on unhandled errors. Mention that the script is idempotent: rerunning is a no-op when both forms already exist.

### Tests for Phase 12 (write first, verify red)

- [ ] T121 [P] In `tests/test_normalise_analysis_sheets.py` add `test_docx_only_folder_produces_png` constructing a temp gram folder containing only `Analysis Sheet.docx` (the minimal docx written via `zipfile`+`xml.etree` per T099), running the normaliser with the renderer stubbed via `--renderer-cmd` pointing at a tiny script that writes a known PNG byte template, and asserting both files exist post-run and the script exits 0.
- [ ] T122 [P] In `tests/test_normalise_analysis_sheets.py` add `test_png_only_folder_produces_docx` constructing a temp gram folder containing only `Analysis.png` and asserting the normaliser produces a valid (zip-openable, parseable) `Analysis Sheet.docx` containing the PNG full-page, with both files present post-run.
- [ ] T123 [P] In `tests/test_normalise_analysis_sheets.py` add `test_both_present_is_idempotent_noop` asserting that a folder containing both files has its mtimes preserved across a run and the run logs an INFO line per folder, not a WARNING.
- [ ] T124 [P] In `tests/test_normalise_analysis_sheets.py` add `test_renderer_failure_is_warning_not_abort` pointing `--renderer-cmd` at a script that exits 1, asserting the affected folder produces a WARNING in the log, the run exits 0, and the missing form is reported in the run summary so the technical author can see it from the CSV via the eventual extractor warning.
- [ ] T125 [P] In `tests/test_normalise_analysis_sheets.py` add `test_missing_both_forms_is_warning` constructing an empty gram folder and asserting the run emits a WARNING (`"analysis sheet missing"`), continues to the next folder, and exits 0.

### Implementation for Phase 12

- [ ] T126 Create `normalise_analysis_sheets.py` at repository root, scaffold `argparse` per T120, wire `setup_logging` to `normalise.log` and stdout per R10 (contracts/cli-contracts.md §`normalise_analysis_sheets.py`)
- [ ] T127 In `normalise_analysis_sheets.py`, implement `iter_gram_folders(content_root: Path) -> Iterator[Path]` that walks the content tree yielding every directory whose name matches `Gram \d+` (sorted, deterministic, no recursion past the gram folder itself)
- [ ] T128 In `normalise_analysis_sheets.py`, implement `classify_folder(folder: Path) -> str` returning `"docx"`, `"png"`, `"both"`, or `"missing"` based on which of `Analysis Sheet.docx` / `Analysis.png` are present
- [ ] T129 In `normalise_analysis_sheets.py`, implement `render_docx_to_png(docx: Path, png_out: Path, renderer_cmd: str) -> bool` via `subprocess.run` invoking LibreOffice headless (`soffice --headless --convert-to png --outdir <tmp> <docx>`) or the configured equivalent; return `True` on success, log WARNING + return `False` on renderer-unavailable or non-zero exit. Never raises.
- [ ] T130 In `normalise_analysis_sheets.py`, implement `wrap_png_in_docx(png: Path, docx_out: Path) -> bool` using stdlib `zipfile` + `xml.etree` (reuse the T099 minimal-docx writer pattern) to embed the PNG full-page. Never raises; returns `False` on filesystem failure.
- [ ] T131 In `normalise_analysis_sheets.py`, implement `main()` orchestration: walk gram folders, classify each, dispatch to renderer or wrapper, accumulate per-folder warnings, log a per-folder INFO/WARNING line, write an end-of-run summary (`folders_visited`, `docx_to_png_rendered`, `png_to_docx_wrapped`, `both_present_skipped`, `renderer_failures`, `missing_analysis`) per FR-014

### Pipeline & contract wiring

- [ ] T132 Update `extract_to_csv.py::gram_to_rows` (T045) so the analysis row populates both `png_path` (from the gram folder's `Analysis.png`) and `analysis_docx_path` (from the gram folder's `Analysis Sheet.docx`). Where either is absent after normalisation, populate the corresponding column with `""` and append `"analysis renderer failed: <direction>"` to the row's `warnings`. Update `write_csv` (T046) column order to include `analysis_docx_path` per contracts/csv-schema.md.
- [ ] T133 Update `tests/test_extract_to_csv.py::test_csv_round_trip_invariant` (T038) for the new column. Add `test_analysis_row_carries_both_paths_when_normaliser_ran` and `test_analysis_row_records_renderer_failure_warning` using a temp content tree with selectively missing files to exercise both happy-path and failure-path columns.
- [ ] T134 Update `run_pipeline.bat` (T082, last updated by T119 for `dita\` output) to insert `python normalise_analysis_sheets.py --content-root %1` as a new stage between the existing extract and pause steps, with `if errorlevel 1 goto error` after the invocation. Update `tests/test_run_pipeline_bat.py` (T080) to assert the new call order `normalise → extract → pause → generate`.
- [ ] T135 [P] In `README.md`, add a `Renderer prerequisites (LibreOffice headless)` section per the new FR-023 assumption: acquisition, install on the development VM and the air-gapped target PC, air-gap transfer, the `--renderer-cmd` override, and an explicit note that the renderer is not bundled and not a Python dependency.
- [ ] T136 [P] In `contracts/csv-schema.md`, verify the column-count assertion (now 16 columns) matches T132's `write_csv` column order; update any worked example whose row width still reflects the pre-FR-023 column count *(already partially done in this phase's spec edits; this task is the consistency sweep after T132 lands).*

**Checkpoint**: After Phase 12, every gram folder under a content root has both `Analysis Sheet.docx` and `Analysis.png` before extraction runs; CSV analysis rows carry both paths; renderer failures are surfaced as row warnings rather than aborts; the batch wrapper threads the new stage in before extraction; FR-022's asset copy in `generate_dita.py` consumes the now-guaranteed `Analysis.png` without needing fallback logic.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — independent of all other stories (consumes only the CSV fixture)
- **User Story 2 (Phase 4)**: Depends on Foundational — independent of US1 / US3 / US4 (uses only the GLC fixtures)
- **User Story 3 (Phase 5)**: Depends on Foundational AND User Story 4 (introspection tests need a mock PPTX generated via `make_mock_pptx`)
- **User Story 4 (Phase 6)**: Depends on Foundational — independent of US1 / US2 / US3
- **User Story 5 (Phase 7)**: Depends on User Stories 1–4 being complete (it asserts properties across all scripts and tests)
- **User Story 6 (Phase 8)**: Depends on User Stories 1 and 2 (the batch wrapper invokes those scripts)
- **Polish (Phase 9)**: Depends on every user story being complete
- **Reverse-Spec Adaptation (Phase 10)**: Depends on Phase 9 and on `source/notes/reverse-spec.md` existing; rewrites Phase 6 deliverables (mock generator), replaces the Phase 4 stub from T044, and extends the Phase 9 README. T101–T103 (mock test updates) and T105 (extractor test updates) follow their corresponding implementation tasks; T106 (DITA-OT README section) and T107 (plan/spec alignment) are independent and can run in parallel with the mock-generator work
- **Self-Contained Publication Tree (Phase 11)**: Depends on Phase 3 (the DITA generator skeleton). Captures the `dita/` asset-copy contract (FR-022) and the `publish_html.py` HTML preview helper (FR-021 extension)
- **Analysis-Sheet Normalisation (Phase 12)**: Depends on Phase 10 (the corpus-aware mock generator's 50/50 docx/png mix is the primary test corpus), on Phase 4 (the extractor that consumes the post-normalisation columns), and is upstream of Phase 11 (FR-022's asset copy assumes the `Analysis.png` exists in the gram folder; FR-023 produces it). T134 depends on Phase 8 (`run_pipeline.bat` exists). T135/T136 are independent README/contract tasks and can run in parallel with the implementation tasks

### Within Each User Story

- Tests come first — write them and verify they fail before implementing
- Helpers (parsers, formatters) before emitters
- Emitters before orchestration `main()`

### Parallel Opportunities

- All Phase 1 tasks except T001 are `[P]` and run together once the directory layout is in place
- All Phase 2 fixture-creation tasks are `[P]`
- Within each user story phase, all `[P]`-marked test tasks run together; all `[P]`-marked implementation helper tasks run together
- Across user stories: US1, US2, and US4 can run in parallel after Foundational; US3 starts once US4 is done; US6 starts once US1 and US2 are done; US5 starts once US1–US4 are done
- All Phase 9 README tasks T083–T090 are `[P]`

---

## Parallel Example: User Story 1

```bash
# Launch all User Story 1 tests together (all touch tests/test_generate_dita.py
# but each is a separate test method, so the underlying file is shared and
# they should be implemented in order; mark only as [P] across files):
Task: "T009 — test_glc_topic_structure"
Task: "T010 — test_analysis_topic_audience_attribute"
Task: "T011 — test_main_ditamap_uses_topichead"
Task: "T012 — test_test_ditamap_is_flat"
Task: "T013 — test_wav_gaps_lite_stub"
Task: "T014 — test_skipped_report_emitted_for_tbd_wav"
Task: "T015 — test_idempotent_output"
Task: "T016 — test_manifest_lists_every_output_file"

# Then launch the helper implementations together (each in its own helper:
# slugify, resolve_image_href, emit_glc_topic, emit_analysis_topic, emit_wav_stub_topic):
Task: "T019 — implement slugify"
Task: "T020 — implement resolve_image_href"
Task: "T021 — implement emit_glc_topic"
Task: "T022 — implement emit_analysis_topic"
Task: "T023 — implement emit_wav_stub_topic"
```

(Note: tasks listed as `[P]` within the same source file are parallelisable in
*planning*, but a single developer editing one file should serialise them.
The `[P]` marker is most useful when the project is staffed by multiple
developers or when an LLM is dispatching independent edits.)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup
2. Phase 2: Foundational (fixtures + logging convention reference)
3. Phase 3: User Story 1 (DITA generation)
4. **STOP and VALIDATE**: Run `python -m unittest tests/test_generate_dita.py` and `python generate_dita.py --csv tests/fixtures/minimal.csv --out tests/_tmp/output --image-root tests/fixtures` end-to-end
5. Demo to the technical author with a hand-authored CSV — this delivers immediate value: any CSV the author can produce by hand becomes a DITA publication

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Hand-authored CSV becomes DITA (MVP)
3. Add User Story 4 → Mock PPTX is now testable
4. Add User Story 3 → Run introspection against real instructor PPTXs to inform the FR-015 stub replacement
5. Add User Story 2 → Hand-authored CSVs replaced by extracted CSVs (still pending the stub replacement, which is a separate, post-handover task)
6. Add User Story 5 → Air-gapped maintenance harness in place
7. Add User Story 6 → One-shortcut Windows orchestrator
8. Phase 9 polish → README, quickstart re-run, Oxygen build verification

### Parallel Team Strategy

With multiple developers post-Foundational:

- Developer A: User Story 1 (DITA generation) — the MVP
- Developer B: User Story 4 (Mock PPTX) — unblocks Developer C
- Developer C: User Story 3 (Introspection) — starts when B reaches T073
- Developer D: User Story 2 (Extraction infrastructure) — independent, pairs with the eventual stub-replacement task

User Story 5 and User Story 6 are coordinated by whichever developer finishes their primary story first.

---

## Notes

- `[P]` tasks = different files, no dependencies on other unfinished tasks
- `[Story]` label maps each task to its user story for traceability against `spec.md`
- Each user story is independently completable and testable per its acceptance scenarios
- Verify each test fails (red) before implementing the matching production code
- Commit after each task or each logical group; the project's hooks auto-commit between speckit phases
- Stop at any checkpoint to validate the story independently
- The shape-grouping function (`extract_grams_from_slide`) remains a documented `NotImplementedError` stub at end of Phase 4 by design (FR-015); replacing it is a separate post-handover task informed by the Phase 5 introspection report

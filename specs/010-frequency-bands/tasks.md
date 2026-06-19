# Tasks: Frequency Bands

**Feature**: `specs/010-frequency-bands/` | **Branch**: `claude/focused-ptolemy-fdl0ah`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests are included per the constitution's Test-First Discipline (Principle III):
every behaviour change gets a stdlib `unittest` regression. Suite must be green
before completion: `python -m unittest discover tests/`.

## Phase 1: Setup

- [X] T001 Confirm the change set is scoped to four canonical scripts plus their tests/fixtures and the canonical contracts; no new files, modules, or dependencies (review `scripts/extract_to_csv.py`, `scripts/generate_dita.py`, `scripts/deduplicate_csv.py`, `scripts/mock_pptx.py`).

## Phase 2: Foundational (blocking prerequisites)

These data-layer changes are read by every user story and MUST land first.

- [X] T002 In `scripts/extract_to_csv.py`, change the `GlcDocument` dataclass: remove the `freq_end` field; add `bandwidth: str = ""` and `bandcentre: str = ""`.
- [X] T003 In `scripts/extract_to_csv.py` `parse_glc`, read `settings/lofar/bandwidth` into `doc.bandwidth` (keep `"GLC missing bandwidth"` warning) and `settings/lofar/bandcentre` into `doc.bandcentre` (new `"GLC missing bandcentre"` warning); never raise.
- [X] T004 In `scripts/extract_to_csv.py`, swap the `freq_end` entry in `CSV_COLUMNS` (position 12) **in place** for `bandwidth`, `bandcentre`.
- [X] T005 In `scripts/extract_to_csv.py` `expand_gram_to_rows` (the GLC-row and analysis-row builders), replace the `freq_end` row key/value with `bandwidth` and `bandcentre` (sourced from the parsed GLC for GLC rows; empty for the analysis row).
- [X] T006 In `scripts/generate_dita.py`, update the `CSV_COLUMNS` constant to mirror the new column order (`freq_end` → `bandwidth`, `bandcentre`).

## Phase 3: User Story 1 — Correct frequency band in the published gram (P1) 🎯 MVP

**Goal**: The GramFrame `gram-config` table shows the true `freq-start`/`freq-end`
derived from `bandwidth`/`bandcentre`.
**Independent test**: Generate a gram from a row with `bandcentre != bandwidth/2`
and assert the table shows the derived limits.

- [X] T007 [US1] In `scripts/generate_dita.py`, add a small deterministic numeric formatter helper (integer results without `.0`; non-integer results trailing-zero-stripped; tolerant of blank/non-numeric input) for frequency limits.
- [X] T008 [US1] In `scripts/generate_dita.py` `_append_gramframe_table`, change its signature/body to accept `bandwidth`/`bandcentre` (instead of `freq_end`) and emit `freq-start = format(bandcentre - bandwidth/2)` and `freq-end = format(bandcentre + bandwidth/2)`; degrade per research R3 (blank `bandcentre` → legacy `0`/`bandwidth`; blank `bandwidth` too → blank values); `time-start`/`time-end` unchanged.
- [X] T009 [US1] In `scripts/generate_dita.py`, update both `_append_gramframe_table` call sites (normal + redirected image rows, ~lines 855 & 866) to pass `row.get("bandwidth")`/`row.get("bandcentre")` instead of `row.get("freq_end")`.
- [X] T010 [P] [US1] In `tests/test_generate_dita.py`, add cases asserting the derived `freq-start`/`freq-end` for the spec spot-checks (400/200→0/400; 400/600→400/800; 100/250→200/300; 401/200.5→0/401), the blank-`bandcentre` legacy fallback, and the blank-`bandwidth` blank output.

## Phase 4: User Story 2 — Author reviews frequency settings in the CSV (P2)

**Goal**: Extraction emits `bandwidth`/`bandcentre` (no `freq_end`).
**Independent test**: Extract over a fixture and assert the CSV header + row
values.

- [X] T011 [US2] Migrate test fixtures to the new schema: update `tests/fixtures/minimal.glc` (and any other fixture `.glc`) to carry `<bandcentre>`, and update `tests/fixtures/minimal.csv` / `tests/fixtures/dedup_source.csv` / `tests/fixtures/audience_minimal.csv` headers+rows to replace `freq_end` with `bandwidth`,`bandcentre` (include at least one band not centred at `bandwidth/2`).
- [X] T012 [US2] In `scripts/mock_pptx.py`, emit `<bandcentre>` alongside `<bandwidth>` in generated GLC files (use representative values, including at least one off-centre band) so the synthetic corpus exercises the new path.
- [X] T013 [P] [US2] In `tests/test_extract_to_csv.py`, update/add cases: CSV header contains `bandwidth`,`bandcentre` and no `freq_end`; GLC-row values are populated from the GLC; analysis row has empty band columns; missing-`bandcentre` records the warning.
- [X] T014 [P] [US2] In `tests/test_glc_parser.py`, update/add cases: `parse_glc` populates `bandwidth` and `bandcentre`; missing `bandcentre` yields empty + `"GLC missing bandcentre"`; malformed/missing file still never raises.

## Phase 5: User Story 3 — Dedup pairs only same-view grams (P3)

**Goal**: "Same frequency view" = same `(bandwidth, bandcentre)` pair.
**Independent test**: Two `.wav` grams with equal `bandwidth` but different
`bandcentre` are NOT paired; identical pairs ARE eligible.

- [X] T015 [US3] In `scripts/generate_dita.py` `_master_index_key`, replace the `freq_end` element of the `.wav` key with `bandwidth` and `bandcentre` (→ `("wav", png_path, time_end, bandwidth, bandcentre)`); update the docstring/log text referencing the `(time_end, freq_end)` view.
- [X] T016 [US3] In `scripts/deduplicate_csv.py`, update any `freq_end`-based "same view" comparison/column handling to use the `(bandwidth, bandcentre)` pair.
- [X] T017 [P] [US3] In `tests/test_deduplicate_csv.py` and `tests/test_generate_dita.py`, add cases: same `bandwidth`+`bandcentre` → eligible to share an asset; same `bandwidth` but different `bandcentre` → distinct views, not redirected.

## Phase 6: Polish & Cross-Cutting

- [X] T018 [P] Update canonical contracts to match: `specs/001-pptx-dita-migration/contracts/glc-schema.md` (add `bandcentre`, drop `freq_end` mapping), `.../csv-schema.md` (column swap + header lines), `.../gramframe.md` (derived freq rows).
- [X] T019 [P] Update `README.md` CSV column reference (swap `freq_end` for `bandwidth`,`bandcentre`).
- [X] T020 Grep the repo for residual `freq_end` references in scripts/tests/fixtures (`rg freq_end scripts tests`) and confirm none remain except intentional historical mentions in spec prose.
- [X] T021 Run the full suite `python -m unittest discover tests/` and confirm green; run the synthetic pipeline (mock → extract → generate) and confirm the CSV header and a sample gram-config table are correct (determinism: re-run generate, byte-identical).

## Dependencies & Execution Order

- **Phase 1 → Phase 2** (foundational data-layer) blocks all user stories.
- **US1, US2, US3** depend on Phase 2; within Phase 2, T002→T003→T005 are
  sequential (same file/regions); T004/T006 are the column-constant edits.
- US1 (T007–T010), US2 (T011–T014), US3 (T015–T017) are largely independent
  after Phase 2; `[P]` test tasks across different files can run in parallel.
- Phase 6 runs last (T021 is the final gate).

## Implementation Strategy

- **MVP = Phase 2 + US1**: the corrected gram-config table is the core defect
  fix. US2 (fixtures/mock + CSV tests) and US3 (dedup key) complete the change.
- Keep edits minimal per Principle II; no new scripts or dependencies.

# Tasks — Week-Based IA

Dependency-ordered. `[P]` = parallelisable with siblings.

## Phase 1 — Extraction (US1: FR-001, FR-002, FR-003)

- [x] T001 Add `week_chapter_number(title)` helper (regex `\bweek\s*0*(\d+)\b`,
      case-insensitive, leading zeros stripped) to `extract_to_csv.py`.
- [x] T002 In the extraction loop, for `publication == "main"` set
      `target_chapter = week_chapter_number(chapter)` and pass `target_doc=""`;
      thread a `target_chapter` parameter through `gram_to_rows`.
- [x] T003 [P] Tests: `Week N` title → `target_chapter == "N"`; Pub10-style
      title → empty; `main` rows have empty `target_doc`.

## Phase 2 — Renumbering (US2: FR-005, FR-006, FR-007, FR-012)

- [x] T010 Add `TARGET_GRAM_ID` constant and `renumber_grams(rows)` to
      `deduplicate_csv.py` per the data-model algorithm (clear-then-recompute,
      bucket by effective chapter/doc, order by source chapter + row index,
      `max+1`).
- [x] T011 Wire `renumber_grams` into `main()`; add `target_gram_id` to
      fieldnames if absent; log each reassignment and a summary.
- [x] T012 [P] Tests: max+1 on collision, first-claimant keeps number, order by
      source chapter then row, idempotent re-run, inert when no collision.

## Phase 3 — Generation (US1+US2+US3: FR-004, FR-008, FR-009, FR-010, FR-011, FR-013)

- [x] T020 Add `_effective_gram_id(row)`; make `_gram_num`/folder/file/id/title
      derive from it; drop the `suffix=` parameter from
      `_gram_folder_name`/`_topic_filename`/`_topic_id`/`_topic_dir_for_row`.
- [x] T021 Expand bare-integer effective chapter to `Week N` / `week-N` in
      `_normalise_chapter`.
- [x] T022 Remove `_compute_gram_suffixes` / `_suffix_for_row`; update
      `build_master_index`, `emit_gram_topic`, `_gram_groups`, `emit_main_ditamap`,
      `emit_test_ditamap`, and `main()` to drop suffix threading and use the
      effective gram id.
- [x] T023 Re-key `check_row_identity` and `_gram_groups` on
      `(publication, effective chapter, effective doc, effective gram number, …)`;
      group the main ditamap by effective chapter.
- [x] T024 Add `target_gram_id` to `generate_dita.OPTIONAL_CSV_COLUMNS`.
- [x] T025 [P] Tests: week expansion, effective-id paths/titles, ditamap-by-week,
      no suffix folders, fail-fast on residual collision (replaces the old
      auto-suffix test).

## Phase 4 — Docs & contracts

- [x] T030 Update `specs/001-pptx-dita-migration/contracts/csv-schema.md`
      (optional `target_gram_id`; `target_chapter` week-int meaning).
- [x] T031 Update `README.md` (pipeline ordering, new column, week IA) and
      `CLAUDE.md` (feature 007 note).

## Phase 5 — Verify

- [x] T040 `python -m unittest discover tests/` green.

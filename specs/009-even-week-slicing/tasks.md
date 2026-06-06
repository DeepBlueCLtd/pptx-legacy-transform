---
description: "Task list for feature 009 — even-slice no-week main decks across the four weeks"
---

# Tasks: Even-slice no-week `main` decks across the four weeks

**Input**: Design documents from `specs/009-even-week-slicing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED. The constitution (Principle III) mandates tests for new
features and a regression test for fixes; each behavioural change below ships
with `unittest` coverage that must fail before and pass after.

**Organization**: By user story (spec.md). The three stories map cleanly to three
separate stage files, so they can be built in parallel; the end-to-end validation
(Phase 6) exercises all three together.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable — different file, no dependency on an incomplete task
- **[Story]**: US1 / US2 / US3 (Setup, Foundational, Polish carry no story label)
- Single-project layout: scripts at repo root, tests under `tests/`

---

## Phase 1: Setup

**Purpose**: Confirm the working baseline; this feature adds no new dependency.

- [ ] T001 Confirm branch `009-even-week-slicing`, run `python -m unittest discover tests/` green as the baseline, and confirm `requirements.txt` is unchanged (no new runtime dependency for this feature).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core prerequisites shared by all stories.

**None.** All three stages (`extract_to_csv.py`, `generate_dita.py`,
`deduplicate_csv.py`) already exist; each story is a self-contained edit to one of
them. No shared scaffolding must land first.

**Checkpoint**: User-story work can begin immediately (in parallel if staffed).

---

## Phase 3: User Story 1 - No-week decks auto-distribute across the four weeks (Priority: P1) 🎯 MVP

**Goal**: A no-week `main` deck (Pub10, Legacy Pub 10) has each gram assigned a
week (`target_chapter` 1–4) by an even slice, with no analyst table.

**Independent Test**: Run `extract_to_csv.py` on a corpus with one no-week `main`
deck of known size G; assert the deck's `target_chapter` values are an even split
(`floor(G/4)` per week, remainder to earliest weeks) in source order.

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL)

- [ ] T002 [P] [US1] Test the even-slice distribution for representative sizes (G=12 → 3/3/3/3; G=10 → 3/3/2/2; G=7 → 2/2/2/1; G=2 → 1/1/0/0) in `tests/test_extract_to_csv.py`.
- [ ] T003 [US1] Test that sliced grams keep **source order** and fall in **contiguous** week blocks (first block → week 1, …), with the week written to `target_chapter`, in `tests/test_extract_to_csv.py`.
- [ ] T004 [US1] Test the scope guards in `tests/test_extract_to_csv.py`: a `Week N`-token `main` deck is NOT sliced (keeps its single week); a `progress test` / `final assessment` deck still routes to its own publication (classification unchanged, FR-001); "Legacy Pub 10" is sliced exactly like Pub10 (no special case, FR-011).

### Implementation for User Story 1

- [ ] T005 [US1] Add a pure, deterministic helper to `extract_to_csv.py` that maps a gram's (source index, deck total G) to its week 1–4 using `base = G//4`, `rem = G%4`, weeks `1..rem` taking `base+1` (contiguous blocks).
- [ ] T006 [US1] In `extract_to_csv.py`'s per-deck extraction pass, for a no-week `main` deck write the helper's week into `target_chapter` (replacing the leave-blank-for-analyst path); leave `Week N`-token decks and non-`main` publications untouched (depends on T005).

**Checkpoint**: A no-week deck's grams carry an even week split in the CSV — US1 is independently testable.

---

## Phase 4: User Story 2 - `main` reads as flat week folders (Priority: P2)

**Goal**: `main` grams land at `main/week-N/gram-NN/` (no source-document tier), and
the generator enforces folder uniqueness on `(publication, week, number)` so the
flat layout is safe.

**Independent Test**: Generate a `main` tree from a hand-built CSV; assert no
folder tier sits between `week-N` and `gram-NN`, the ditamap hrefs carry no
doc-slug segment, and two distinct grams sharing `(week, number)` fail fast.

### Tests for User Story 2 ⚠️ (write first, ensure they FAIL)

- [ ] T007 [P] [US2] Test that a `main` gram's topic path is `main/week-N/gram-NN/` with **no** doc-slug tier, in `tests/test_generate_dita.py`.
- [ ] T008 [US2] Test that `emit_main_ditamap` topicref hrefs are `main/week-N/gram-NN/gram_NN.dita` with no doc-slug segment, in `tests/test_generate_dita.py`.
- [ ] T009 [US2] Test that two distinct `main` grams at the same `(week, number)` trigger the fail-fast (collision key drops `effective_doc` for `main`), and that non-`main` collision behaviour is unchanged, in `tests/test_generate_dita.py`.

### Implementation for User Story 2

- [ ] T010 [US2] In `generate_dita.py` `_publication_root`, stop appending the `doc_slug` segment for `main` (non-`main` unchanged).
- [ ] T011 [US2] In `generate_dita.py` `emit_main_ditamap`, drop the `doc_slug` segment from the topicref href (keeping the existing empty-segment filtering) (depends on T010 conceptually; same file).
- [ ] T012 [US2] In `generate_dita.py` `check_row_identity`, drop `effective_doc` from the collision key for `main` so uniqueness is `(publication, effective_chapter, effective number)`; keep `effective_doc` for non-`main`.

**Checkpoint**: `main` publishes flat and a residual collision is caught, not overwritten — US2 is independently testable.

---

## Phase 5: User Story 3 - Every `main` gram has a unique, traceable number (Priority: P2)

**Goal**: The renumber step assigns collision-free `main` numbers under a
selectable scheme — **continuous** (default) or **per-week** — recording the
number in `target_gram_id` without mutating `gram_id`.

**Independent Test**: Run `deduplicate_csv.py` on a sliced CSV once per scheme;
assert numbers are folder-unique, continuous gives a contiguous `1..N` across
weeks, per-week restarts each week at 1, `gram_id` is preserved, and non-`main`
publications are untouched.

### Tests for User Story 3 ⚠️ (write first, ensure they FAIL)

- [ ] T013 [P] [US3] Test the **continuous** scheme: `main` numbered `1..N` over `(week, source-chapter, row-order)`, week N starting at one past week N-1's maximum, in `tests/test_deduplicate_csv.py`.
- [ ] T014 [US3] Test the **per-week** scheme: each `(main, week)` numbered `1..k` from 1, in `tests/test_deduplicate_csv.py`.
- [ ] T015 [US3] Test that `--main-numbering` selects the scheme and **defaults to continuous**, that the number lands in `target_gram_id`, and that `gram_id` is never mutated, in `tests/test_deduplicate_csv.py`.
- [ ] T016 [US3] Test that non-`main` publications are unaffected by the flag/scheme, and that the renumber is idempotent under both schemes (re-run is byte-identical), in `tests/test_deduplicate_csv.py`.

### Implementation for User Story 3

- [ ] T017 [US3] Add `--main-numbering {continuous,per-week}` (default `continuous`) to `deduplicate_csv.py`'s argument parser, threaded into `renumber_grams`.
- [ ] T018 [US3] In `deduplicate_csv.py` `renumber_grams`, branch on publication: for `main` assign numbers per the chosen scheme (continuous = publication-wide `1..N` in `(week, source-chapter, row-order)`; per-week = `1..k` per `(main, week)`); leave non-`main` on the existing `(publication, chapter, doc)` bump-on-collision path (depends on T017).

**Checkpoint**: Sliced `main` grams get collision-free numbers under either scheme — US3 is independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T019 [P] End-to-end test: a corpus with a no-week deck + native week decks runs extract → dedupe (once per scheme) → `publish_html.stage`; assert every staged `main` ditamap href resolves to a real topic file and no two grams share a folder (extend the `StagedHrefsResolveTests` pattern) in `tests/test_publish_html.py`.
- [ ] T020 [P] Determinism/idempotency test in `tests/test_deduplicate_csv.py`: re-running the renumber over the same CSV yields a byte-identical `target_gram_id` under **both** schemes, and (alongside the existing generator idempotency tests) the slice + generate output is byte-stable (FR-010, Principle V).
- [ ] T021 [P] Update `README.md`: in the CSV column reference, change `target_chapter` from "left blank for an analyst" to "auto-filled by the even slice for no-week `main` decks (editable)"; document the new `--main-numbering` flag; note the flat `main/week-N/gram-NN/` layout.
- [ ] T022 Update in-tree fixtures / `source.csv` only as needed to keep the suite green under the flat layout + new numbering (delete superseded shapes per the development-phase posture).
- [ ] T023 Run `python -m unittest discover tests/` and confirm green; confirm no new runtime dependency and Python 3.9 compatibility (`from __future__ import annotations`, no 3.10+ APIs).

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)**: none — start immediately.
- **Foundational (P2)**: empty — no blocker.
- **User stories (P3–P5)**: each depends only on Setup. They touch three different
  files (`extract_to_csv.py`, `generate_dita.py`, `deduplicate_csv.py`), so they
  can proceed in parallel.
- **Polish (P6)**: depends on US1+US2+US3 (the end-to-end and determinism tests
  exercise all three; the README update reflects all three).

### User-story dependencies & coupling

- **US1** — fully independent (CSV-level).
- **US2** — independently testable (tree-level, hand-built CSV). Its fail-fast
  (T012) is what keeps the flat layout safe even before US3 lands.
- **US3** — independently testable (CSV-level). Its numbers only become
  *folder*-unique end-to-end in combination with US2's flat layout, but the
  renumber logic and its tests stand alone.
- **End-to-end value** (a no-week deck publishing correctly into the weeks)
  requires all three; that's what Phase 6 validates.

### Within each story

- Write the story's tests first and confirm they fail, then implement.
- Same-file tasks run in sequence (e.g. T010 → T011 → T012 in `generate_dita.py`).

### Parallel opportunities

- The story-leading test tasks **T002 / T007 / T013** are in three different test
  files → parallelizable.
- With three developers, US1 / US2 / US3 can be built concurrently (different
  source files) after Setup.
- Polish tasks **T019 / T020 / T021** touch different files → parallelizable.

---

## Parallel Example: kick off all three stories' tests

```bash
# Different test files — safe to write in parallel:
Task: "T002 even-slice distribution tests in tests/test_extract_to_csv.py"
Task: "T007 flat main layout test in tests/test_generate_dita.py"
Task: "T013 continuous-scheme renumber test in tests/test_deduplicate_csv.py"
```

---

## Implementation Strategy

### MVP first (User Story 1)

1. Phase 1 Setup → 2. Phase 3 US1 (even slice) → 3. **STOP & validate**: a no-week
   deck shows an even week split in the CSV. That alone unblocks the analyst from
   the missing stakeholder table.

### Incremental delivery

1. US1 (slice) → CSV shows weeks.
2. US2 (flat layout + safe collision scope) → `main` publishes flat; collisions
   caught.
3. US3 (numbering toggle) → collisions resolved, scheme selectable.
4. Phase 6 → end-to-end + determinism + docs.

### Default-scheme note (non-blocking)

The author's choice of default numbering scheme is **not** on the critical path:
both schemes are built in US3, and the default is the single `default=` on the
`--main-numbering` flag (T017). Flip it in one line if/when the author picks
per-week; no other task changes.

---

## Notes

- `[P]` = different file, no incomplete dependency.
- Tests must fail before implementation (Principle III); the canonical suite must
  be green before merge.
- Determinism (Principle V) is a first-class acceptance criterion, not an
  afterthought — T020 guards it under both schemes.
- Commit after each task or logical group; stop at any checkpoint to validate a
  story independently.

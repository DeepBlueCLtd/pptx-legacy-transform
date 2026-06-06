# Phase 1 Data Model: Even-slice no-week `main` decks

This feature adds no new files or columns; it changes how three existing CSV
columns are populated/consumed and how `main` paths are shaped. Entities below
are the conceptual data, not new storage.

## Entities

### No-week `main` deck

A source document that classifies to `main` (not progress-test, not
final-assessment) and whose folder title carries **no** `Week N` token.
Examples: `Pub10`, `Legacy Pub 10`. The unit that gets sliced.

- **G** — the count of distinct grams the deck contributes.
- Grams have a stable **source order** (the order extraction already emits).

### Week assignment — `target_chapter` (existing, editable)

Which of the four weeks a gram lands in.

- **Week-token deck**: `target_chapter = N` (the parsed week), as today.
- **No-week `main` deck (new)**: `target_chapter` = the week of the contiguous
  block the gram's source index falls in (R1):
  - `base = floor(G / 4)`, `rem = G mod 4`.
  - Weeks `1..rem` hold `base + 1` grams; weeks `rem+1..4` hold `base`.
  - The first block → week 1, the next → week 2, … (source order preserved).
- Remains **author-editable**: a reviewer may override any gram's week.
- Effective chapter = `target_chapter` if set, else `chapter` (unchanged rule).

### Effective gram number — `target_gram_id` (existing, additive)

The number that drives the folder (`gram-NN`), topic filename, topic id and
title. `gram_id` is never mutated; effective number = `target_gram_id or gram_id`.

- Populated by `deduplicate_csv.py` for `main` according to the chosen scheme:
  - **continuous**: `1..N` over all `main` grams ordered by
    `(week, source-chapter, row-order)` — contiguous per-week blocks in week
    order (week N starts at week N-1's max + 1).
  - **per-week**: `1..k` within each `(main, week)`, ordered by
    `(source-chapter, row-order)`.
- Non-`main` publications: unchanged (bump a taken number to bucket max + 1 within
  `(publication, chapter, doc)`).

### `main` numbering space

The set of effective numbers in `main`. **Invariant**: no two `main` grams share
an output folder `main/week-N/gram-NN/`, i.e. `(week, effective number)` is
unique. Continuous satisfies this with publication-wide-unique numbers; per-week
satisfies it with week-unique numbers plus the distinct `week-N` path segment.

### `main` output path (changed)

`main/week-N/gram-NN/` — **no** `doc-slug` tier between week and gram. Each
referenced asset is still copied beside the topic with a stable bare-filename
href (unchanged). Non-`main` publications keep their existing layout.

## Validation rules

- **VR-1 (distribution)**: each no-week deck's per-week gram counts differ by at
  most 1; every gram lands in exactly one week; `G < 4` leaves later weeks empty
  for that deck (no empty `gram-` folders).
- **VR-2 (folder uniqueness)**: `(publication=main, week, effective number)` is
  unique across the corpus; a violation is a fail-fast in the generator pointing
  to the dedupe step (not a silent overwrite).
- **VR-3 (traceability)**: every renumbered row keeps its original `gram_id`; the
  assigned number lives only in `target_gram_id`.
- **VR-4 (determinism)**: slice and renumber are pure functions of stable source
  order; identical CSV ⇒ identical `target_chapter`, `target_gram_id`, output.
- **VR-5 (scope)**: classification and non-`main` numbering are unchanged; only
  no-week `main` decks are sliced and only `main` uses the scheme toggle.

## State / flow

```text
extract_to_csv.py   → assigns target_chapter (week) per gram   [slice]
        │              (no-week main deck → even blocks; week-token deck → its week)
        ▼
deduplicate_csv.py  → assigns target_gram_id (number) for main  [renumber, scheme toggle]
        │              (continuous | per-week); non-main bump-on-collision
        ▼
generate_dita.py    → main/week-N/gram-NN/ ; fail-fast on residual (week,number) clash
```

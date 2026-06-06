# Quickstart: Even-slice no-week `main` decks

How to exercise feature 009 once implemented. Same five-stage pipeline; the only
new surface is the `--main-numbering` flag on the dedupe step.

## Run the flow (POSIX dev host)

```bash
# 1. Extract — no-week main decks (Pub10, Legacy Pub 10) are auto-sliced across
#    the four weeks; their target_chapter is filled with the assigned week.
python extract_to_csv.py --input-root path/to/content --out extracted.csv

# 2. (human) review extracted.csv in Excel. Optional: override any auto-sliced
#    target_chapter; the slice is just the default.

# 3. Renumber — assign collision-free main numbers. Default scheme is continuous.
python deduplicate_csv.py --csv extracted.csv --image-root path/to/content \
    --out extracted.dedup.csv
#    Per-week restart instead (once the author chooses it):
#    python deduplicate_csv.py ... --main-numbering per-week

# 4. Generate — main grams land at dita/main/week-N/gram-NN/ (no doc tier).
python generate_dita.py --csv extracted.dedup.csv --out dita/ \
    --image-root path/to/content
```

## What to verify

- **Slice**: in `extracted.csv`, a no-week deck's `target_chapter` values are
  `1..4` with per-week counts differing by at most one, in source order.
- **Layout**: `dita/main/week-1/gram-01/…` exists with **no** source-document
  folder between `week-1` and `gram-01`.
- **Numbering**:
  - `continuous` → `main` gram numbers are contiguous `1..N` across the weeks;
    week 2 begins right after week 1's last number.
  - `per-week` → each `week-N` starts at `gram-01`.
- **Uniqueness**: no two `main` grams share a `week-N/gram-NN` folder; a deliberate
  residual collision (skip the dedupe step) fails the generator with a message
  naming the dedupe step.
- **Traceability**: a renumbered row keeps its original `gram_id`; the new number
  is in `target_gram_id`.
- **Determinism**: re-running steps 1, 3, 4 over unchanged input yields
  byte-identical CSV/DITA under either scheme.

## Flip the default scheme (after the author decides)

The default is `continuous`. To make `per-week` the default, change the single
`default=` on the `--main-numbering` argument in `deduplicate_csv.py` (and update
its tests). No other stage changes — extract and generate are scheme-agnostic.

## On the air-gapped target

Same as the README cold-start, via the wrappers: `extract.py` → review →
`dedupe.py` → `write.py` → `publish.py`. Pass the scheme through the dedupe
wrapper's `sys.argv` (e.g. add `--main-numbering per-week`) if/when the author
picks per-week; otherwise the continuous default applies with no change.

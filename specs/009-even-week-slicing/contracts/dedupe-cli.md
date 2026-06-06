# Contract: `deduplicate_csv.py` CLI — `--main-numbering`

## New flag

```
--main-numbering {continuous,per-week}    (default: continuous)
```

Selects how `main` gram numbers are assigned during renumbering. It is the **only**
control for the numbering scheme; no other stage reads it.

| Value | Behaviour for `main` |
|---|---|
| `continuous` (default) | One sequence across the four weeks: order all `main` grams by `(week, source-chapter, row-order)` and assign `1..N`. Week N starts at one past week N-1's maximum (inserting grams into an earlier week shifts later weeks' starting numbers). |
| `per-week` | Each week numbered independently: within each `(main, week)`, order by `(source-chapter, row-order)` and assign `1..k`. |

- The assigned number is written to `target_gram_id`; `gram_id` is never mutated.
- **Non-`main` publications are unaffected** by this flag — they keep the existing
  per-`(publication, chapter, doc)` bump-on-collision renumbering.
- The default is provisional (pending the document author). Changing it is a
  one-line `default=` edit; no other behaviour depends on which is default.

## Invariants

- **Idempotent / deterministic**: the same input CSV + same flag value produces a
  byte-identical output CSV (`target_gram_id` cleared and recomputed each run;
  ordering key is stable). Re-running is a no-op.
- **Inert when not needed**: a corpus with no `main` collisions still runs; with
  `continuous` it produces a contiguous `1..N` (which may equal the input if it
  was already contiguous), with `per-week` a `1..k` per week.
- Existing flags/columns (`master_png_path` deduplication, `--image-root`, etc.)
  are unchanged and compose with this flag.

## Example

```bash
# default (continuous) — main numbered 1..N across the weeks
python deduplicate_csv.py --csv signed.csv --image-root source/ --out signed.dedup.csv

# per-week restart, once the author chooses it
python deduplicate_csv.py --csv signed.csv --image-root source/ --out signed.dedup.csv \
    --main-numbering per-week
```

# Contract: `deduplicate_csv.py` CLI — `--main-numbering`

## New flag

```
--main-numbering {continuous,per-week}    (default: per-week)
```

Selects how `main` gram numbers are assigned during renumbering. It is the **only**
control for the numbering scheme; no other stage reads it.

| Value | Behaviour for `main` |
|---|---|
| `per-week` (default) | Each week numbered independently as contiguous `1..k` (no gaps, restart at 1 per week). Order within a week is `(native-week-deck first, source-chapter, row-order)`: a deck whose title carries the week's own "Week N" token keeps the low numbers and leads the page, with any sliced no-week deck (Pub10) following as the contiguous tail. This closes the native-number gaps/jumps that read as "missing numbers" (issue #102). |
| `continuous` | One sequence across the four weeks: order all `main` grams by `(week, source-chapter, row-order)` and assign `1..N`. Week N starts at one past week N-1's maximum (inserting grams into an earlier week shifts later weeks' starting numbers). |

- The assigned number is written to `target_gram_id`; `gram_id` is never mutated.
- **Non-`main` publications are unaffected** by this flag — they keep the existing
  per-`(publication, chapter, doc)` bump-on-collision renumbering.
- `per-week` is the implemented default (issue #102). Changing it is a one-line
  `default=` edit; no other behaviour depends on which is default.

## Invariants

- **Idempotent / deterministic**: the same input CSV + same flag value produces a
  byte-identical output CSV (`target_gram_id` cleared and recomputed each run;
  ordering key is stable). Re-running is a no-op.
- **Inert when not needed**: a corpus already numbered to match the scheme runs as
  a no-op (`target_gram_id` stays empty where `gram_id` already equals the assigned
  number); `continuous` produces a contiguous `1..N`, `per-week` a `1..k` per week.
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

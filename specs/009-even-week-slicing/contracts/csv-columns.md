# Contract: CSV columns touched by feature 009

This feature adds **no new columns**. It changes how two existing additive columns
are populated/consumed. The canonical column reference lives in the README and
`specs/001-pptx-dita-migration/contracts/`; only the deltas are below. Identity
columns (`publication`, `chapter`, `gram_id`, `topic_type`, `sequence`,
`topic_filename`) are unchanged and remain non-editable.

## `target_chapter` (existing; editable)

| Aspect | Before (feature 008) | After (feature 009) |
|---|---|---|
| Week-token `main` deck | bare week integer `N` from the `Week N` title token | unchanged |
| **No-week `main` deck** (Pub10, Legacy Pub 10) | left **blank** for an analyst to fill from a stakeholder table | **auto-filled** with the even-slice week (`1..4`) by `extract_to_csv.py` |
| Editability | editable | editable — a reviewer may override any auto-sliced week |
| Effective chapter | `target_chapter or chapter` | unchanged |

- Distribution rule: `base = floor(G/4)`, `rem = G mod 4`; weeks `1..rem` get
  `base+1`, the rest get `base`; contiguous blocks in source order.

## `target_gram_id` (existing; additive)

| Aspect | Before | After |
|---|---|---|
| Non-`main` publications | bump a taken number to bucket max+1 within `(publication, chapter, doc)` | unchanged |
| **`main`** | per-`(publication, chapter, doc)` bump | reassigned per the chosen scheme over `main` (see `dedupe-cli.md`): **per-week** (default) = contiguous `1..k` within each week, native-week deck first; **continuous** = `1..N` over `(week, source-chapter, row-order)` |
| `gram_id` | never mutated | never mutated |
| Effective number | `target_gram_id or gram_id` | unchanged |

## Round-trip / compatibility

- Both columns are additive and read with an empty default; a CSV produced before
  this feature still parses (a blank `target_chapter` on a no-week `main` deck now
  simply means "not yet sliced", and the slice fills it on the next extract).
- UTF-8-sig, CRLF, `QUOTE_MINIMAL` writing is unchanged.

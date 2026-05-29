# Phase 1 Data Model — Week-Based IA

## Entity 1 — `target_chapter` (existing column, new `main` semantics)

| Field | Value |
|---|---|
| Column | `target_chapter` (editable; already present since feature 005) |
| `main` value | A bare integer `1`…`4` (the week). Empty falls back to `chapter`. |
| Set by | Extraction (from a `Week N` deck title) or an analyst (Pub10 grams). |
| Non-main | Unchanged (empty / source title as before). |

**Effective chapter** = `target_chapter` if non-empty else `chapter`. A
purely-numeric effective chapter `N` expands to navtitle `Week N` and slug
`week-N` (see `contracts/week-chapter-mapping.md`).

## Entity 2 — `target_gram_id` (new optional right-edge column)

| Field | Value |
|---|---|
| Column | `target_gram_id` |
| Position | Right edge, after `master_png_path` (additive; legacy CSVs omit it). |
| Written by | `deduplicate_csv.py` renumber pass (not the extractor). |
| Semantics | The renumbered gram number. **Empty = unchanged**, use `gram_id`. |
| Value form | Bare integer string (`"11"`). |
| `gram_id` | Never mutated — kept as immutable provenance. |

**Effective gram number** = digits of (`target_gram_id` if non-empty else
`gram_id`), zero-padded to two for on-disk names (`gram-11/gram_11.dita`,
`id="gram_11"`, title `Gram 11`).

## Entity 3 — Distinct gram (renumbering unit)

The rows sharing `(publication, chapter, gram_id, vessel_name)` — one gram's
analysis row plus its N lofar rows. Renumbering assigns one value to the whole
unit; every row of the gram receives the same `target_gram_id`.

## Renumbering algorithm (deterministic)

```
clear target_gram_id on every row            # idempotency: recompute each run
group rows into buckets by (publication, effective_chapter, effective_doc)
for each bucket:
    distinct grams = unique (chapter, gram_id, vessel_name), recording first row index
    order grams by (chapter, first_row_index)          # FR-006
    used = set()                                        # numbers claimed in this bucket
    for gram in ordered grams:
        n = int(digits(gram_id))
        if n in used:
            n = max(used) + 1                           # FR-005: one past current maximum
            write str(n) into target_gram_id of every row of this gram
        used.add(n)
```

A gram whose original number is free keeps it (empty `target_gram_id`). A gram
whose number is taken is appended past the running maximum and its new number
joins `used`, so successive collisions step `max+1, max+2, …`.

## Row-identity (fail-fast) key

The generator validates uniqueness on
`(publication, effective_chapter, effective_doc, effective_gram_number,
topic_type, sequence)`. A duplicate means two distinct grams resolve to the same
week + number without renumbering → abort with a per-collision error (FR-010).

## Topic grouping key

One topic per `(publication, effective_chapter, effective_doc,
effective_gram_number)`. With renumbering applied, distinct grams have distinct
effective numbers, so each forms its own topic; no letter suffix is used.

## Invariants

- **Inert by default**: no `target_gram_id` column ⇒ numbering from `gram_id`,
  output identical to pre-feature (FR-011).
- **Idempotent**: clear-then-recompute ⇒ a second renumber run is byte-identical
  (FR-012).
- **CSV file contract preserved**: utf-8-sig, CRLF, QUOTE_MINIMAL on write.
- **Provenance preserved**: `gram_id` and `topic_filename` untouched.

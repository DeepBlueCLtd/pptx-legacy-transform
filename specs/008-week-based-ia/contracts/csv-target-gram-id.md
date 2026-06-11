# Contract — `target_gram_id` column and renumbering

## Column

- **Name**: `target_gram_id`
- **Optionality**: optional, right-edge. Added by `deduplicate_csv.py` if
  absent; the extractor does not emit it. A CSV lacking the column behaves as if
  every cell were empty (forward-compatible, like `master_png_path`).
- **Editable?**: machine-populated. An analyst may override a value, but the
  normal flow is to let the renumber step compute it.
- **Value**: a bare integer string (`"11"`) or empty. **Empty means "unchanged —
  use `gram_id`"**.

## Effective gram number

Consumers MUST compute the gram's number as:

```
effective = target_gram_id.strip() or gram_id
number    = first run of digits in `effective`   # e.g. "Gram 11" → "11" → "11"
```

and derive folder (`gram-NN`), topic filename (`gram_NN.dita`), topic id
(`gram_NN`), and visible title (`Gram NN`) from that number, zero-padded to two.

`gram_id` and `topic_filename` MUST NOT be mutated by renumbering.

## Renumbering rules (`deduplicate_csv.py`)

1. **Reset**: clear every row's `target_gram_id` before computing (idempotency).
2. **Bucket**: group rows by `(publication, effective_chapter, effective_doc)`,
   where `effective_chapter = target_chapter or chapter`,
   `effective_doc = target_doc or ""`.
3. **Distinct grams**: within a bucket, the unit is a unique
   `(chapter, gram_id, vessel_name)`; record the index of its first row.
4. **Order**: process distinct grams by `(chapter, first_row_index)` — source
   chapter alphabetical, then CSV row order.
5. **Assign**: maintain `used` (numbers claimed in this bucket). For each gram,
   let `n = int(digits(gram_id))`. If `n` is already in `used`, set
   `n = max(used) + 1` and write `str(n)` into `target_gram_id` for **every row
   of that gram**. Add `n` to `used`. A gram whose number is free keeps it with
   an empty `target_gram_id`.

## Logging

Each reassignment logs `gram renumbered: chapter=<week> gram_id=<old> → <new>`
at INFO; a summary logs the count of renumbered grams. Mirrors the large-asset
pass's dual stdout + `dedup.log` handlers.

## Invariants

- Re-running over an unchanged CSV yields a byte-identical CSV.
- A bucket with no number collisions leaves every `target_gram_id` empty.
- The CSV file contract (utf-8-sig, CRLF, QUOTE_MINIMAL) is preserved on write.

# Contract: `master_png_path` CSV column

Extends the intermediate CSV schema
(`specs/001-pptx-dita-migration/contracts/csv-schema.md`) with one optional,
additive column that carries large-asset deduplication redirects.

## Column

| Aspect | Value |
|---|---|
| Name | `master_png_path` |
| Position | **right edge** — appended after the current last column |
| Required on read? | **No.** `generate_dita.py` reads it with `row.get("master_png_path", "")` and does **not** add it to the strict required-column set in `read_csv`. A CSV without this column (e.g. the current 16-column `source.csv`, or any legacy CSV) is valid and produces byte-identical output (FR-010, SC-005). |
| Written by | `deduplicate_csv.py` only. The extractor (`extract_to_csv.py`) does **not** emit it (extraction is out of scope). |
| Type | string — a **source-relative asset path**, in the same coordinate space as `png_path` (resolved against `--image-root`). Or empty. |

## Semantics

- **Empty** → the row is not redirected. True for: the master row of a duplicate
  group, any non-duplicate row, every row of an unprocessed CSV.
- **Non-empty** → the row is redirected. The value is the **`png_path` of the
  master row** (the first occurrence of the duplicated asset) that this row's
  lofar must link to instead of copying its own asset.

## Detection rules (how `deduplicate_csv.py` populates it)

1. **Candidate filter** — a row is eligible only if `int(file_size)` exists and
   is **strictly greater than** the threshold (`--threshold-bytes`, default
   `10 * 1024 * 1024` = 10,485,760). At-or-below-threshold rows are never
   redirected, even if duplicated (FR-003).
2. **Grouping** — candidates are grouped by **content identity**: `file_size`
   pre-filter, confirmed by `sha256` of `image_root / png_path`. A group with a
   single member (unique large asset) is left untouched.
3. **Master nomination** — within a ≥2-member group, the **first occurrence** in
   deterministic order (sort by the row-identity tuple `(publication, chapter,
   gram_id, topic_type, sequence)`) is the master; its `master_png_path` stays
   empty.
4. **Redirection** — every other member's `master_png_path` is set to the
   master's `png_path`.
5. **Audio pairs** — for a `.wav` candidate, the unit is the `.glc`/`.wav` pair;
   detection keys on the large `.wav` (the file over threshold). The redirect is
   recorded on the `.wav` row exactly as above; the generator maps it to the
   master `.glc` link at export time (see `dita-provenance-data.md`).

## Invariants

- A non-empty `master_png_path` MUST match an existing non-redirected row's
  `png_path` in the same CSV. If the generator cannot resolve it, the row is
  treated as non-redirected and a WARNING is logged (FR-014).
- The master row is never itself redirected (so the master gram stays a
  self-contained, movable pair).
- Round-trip fidelity: `deduplicate_csv.py` preserves the CSV file-level contract
  — UTF-8 with BOM (`utf-8-sig`), `,` delimiter, `csv.QUOTE_MINIMAL`, `\r\n`
  line terminator, header row — and re-running it over identical inputs yields a
  byte-identical CSV (FR-013, SC-006).

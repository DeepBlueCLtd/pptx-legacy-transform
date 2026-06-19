# Phase 1 Data Model: Frequency Bands

## Entity: GLC band settings

Parsed from a `.glc` file by `parse_glc` into the `GlcDocument` dataclass.

| Field        | Source (GLC path)            | Type (string) | Missing behaviour                          |
|--------------|------------------------------|---------------|--------------------------------------------|
| `bandwidth`  | `settings/lofar/bandwidth`   | numeric str   | `""` + warning `"GLC missing bandwidth"`   |
| `bandcentre` | `settings/lofar/bandcentre`  | numeric str   | `""` + warning `"GLC missing bandcentre"`  |

`GlcDocument.freq_end` is **removed**; replaced by `bandwidth` and `bandcentre`.
`time_end` (from `bottom_crop`) and `image_filename` are unchanged.

**Derivation (consumer-side, not stored on the GLC entity):**

```
freq_start = bandcentre - bandwidth / 2
freq_end   = bandcentre + bandwidth / 2
```

Special case `bandcentre == bandwidth / 2` ⇒ `freq_start = 0`,
`freq_end = bandwidth` (legacy behaviour).

## Entity: CSV row (gram view)

`CSV_COLUMNS` change — `freq_end` swapped **in place** for two columns:

Before: `… time_end, freq_end, png_path, …`
After:  `… time_end, bandwidth, bandcentre, png_path, …`

- Both new columns are **author-editable** (not identity columns).
- Encoding/line-ending/quoting unchanged (UTF-8-with-BOM, CRLF, QUOTE_MINIMAL).
- The analysis row carries empty `bandwidth`/`bandcentre` (as it did empty
  `freq_end`).
- Readers access by name; `freq_end` no longer read anywhere.

## Entity: GramFrame `gram-config` table

The four metadata rows become:

| Label        | Value (before)     | Value (after)                                  |
|--------------|--------------------|------------------------------------------------|
| `time-start` | `0`                | `0` (unchanged)                                |
| `time-end`   | `time_end`         | `time_end` (unchanged)                         |
| `freq-start` | `0` (hardcoded)    | `format(bandcentre - bandwidth/2)`             |
| `freq-end`   | `freq_end`         | `format(bandcentre + bandwidth/2)`             |

`format(...)` = deterministic numeric formatting (R1): integer results without
`.0`; non-integer results trailing-zero-stripped. When `bandwidth`/`bandcentre`
are blank/non-numeric, fall back to legacy (`freq-start = 0`,
`freq-end = bandwidth`) and, if `bandwidth` is also blank, emit blank — never
crash (R3, missing-asset-dangles).

## Dedup view-key

`.wav` master-index key (in `generate_dita.py`):

Before: `("wav", png_path, time_end, freq_end)`
After:  `("wav", png_path, time_end, bandwidth, bandcentre)`

`deduplicate_csv.py` "same view" comparison updated from `freq_end` to the
`(bandwidth, bandcentre)` pair. Image-row keys remain path-only.

# Contract delta: CSV schema — `freq_end` → `bandwidth`, `bandcentre`

Amends `specs/001-pptx-dita-migration/contracts/csv-schema.md`.

## Column change (swap in place)

The single column at position 12 (`freq_end`) is replaced **in place** by two
columns: `bandwidth` then `bandcentre`. All other columns keep their order.

| # | Column        | Type   | Required                              | Notes                          |
|---|---------------|--------|--------------------------------------|--------------------------------|
| 12 | `bandwidth`  | string | when GLC present (else empty)        | numeric string, no units       |
| 13 | `bandcentre` | string | when GLC present (else empty)        | numeric string, no units       |

Both columns are **author-editable** (not identity columns). The analysis row
carries empty `bandwidth`/`bandcentre`. Encoding/line-endings/quoting unchanged
(UTF-8-with-BOM, CRLF, QUOTE_MINIMAL).

## Header (after)

```text
publication,chapter,target_doc,target_chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,bandwidth,bandcentre,png_path,target_ext,file_size,wav_treatment,warnings
```

(`freq_end` removed; `bandwidth`,`bandcentre` inserted at its position.)

## Pre-production note

No backward-compatibility binding (constitution, Development-Phase Posture):
in-tree CSV fixtures are migrated to the new shape; the old `freq_end` shape is
deleted, not preserved.

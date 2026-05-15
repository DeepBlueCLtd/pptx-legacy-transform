# Intermediate CSV Schema

The intermediate CSV is the contract between Stage 2 (`extract_to_csv.py`)
and Stage 4 (`generate_dita.py`), with a Stage 3 human-review step in the
middle. It is the authoritative source the generator consumes — the
generator never re-reads PPTX or GLC files.

## File-level

| Aspect | Value |
|---|---|
| Encoding | UTF-8 with BOM (`utf-8-sig`) |
| Delimiter | `,` (comma) |
| Quoting | `csv.QUOTE_MINIMAL` |
| Line terminator | `\r\n` (Windows-friendly) |
| Header row | Required; column names exactly as below |

## Columns

| # | Column | Type | Empty allowed? | Notes |
|---|---|---|---|---|
| 1 | `publication` | string | no | `main` or `progress-test-N` |
| 2 | `chapter` | string | yes (when publication is a test) | human-readable chapter title |
| 3 | `gram_id` | string | no | format `"Gram NN"`; may be `"Gram 100+"` if corpus grows |
| 4 | `vessel_name` | string | yes | instructor-only content |
| 5 | `topic_type` | enum | no | `glc` or `analysis` |
| 6 | `sequence` | string | no | `1`-based per gram, scoped per `topic_type` |
| 7 | `topic_filename` | string | no | `gram_NN.dita`; identical across every row that belongs to the same gram (CSV's N+1 rows per gram collapse into one DITA topic — see `dita-topic-schema.md` §1) |
| 8 | `display_text` | string | yes (analysis rows) | human-readable link label from the PPTX run |
| 9 | `link_href` | string | yes (analysis rows) | raw hyperlink URI from the PPTX run; `.glc`, `.wav`, or other; source of truth for WAV detection and `xref href` in WAV stub topics |
| 10 | `glc_path` | string | yes (analysis rows; empty for WAV) | resolved `.glc` path relative to source folder; empty when the link target was a `.wav` |
| 11 | `time_end` | string | yes (when GLC missing or analysis row) | numeric string, no units |
| 12 | `freq_end` | string | yes (when GLC missing or analysis row) | numeric string, no units |
| 13 | `png_path` | string | yes (glc rows, analysis rows, WAV-link rows) | path of the asset to copy next to the topic, resolved relative to `--image-root`. Holds the PNG for screenshot grams, the analysis-sheet PNG for analysis rows (populated from the gram folder's `Analysis.png` after FR-023 normalisation; may be empty if the renderer failed), and the `.wav` file for WAV-link rows. |
| 14 | `analysis_docx_path` | string | yes (non-analysis rows; analysis rows when renderer failed) | resolved relative to `--image-root`; populated for analysis rows from the gram folder's `Analysis Sheet.docx` after FR-023 normalisation. Carried for the author's review trail; the generator does not consume it. |
| 15 | `wav_treatment` | enum | yes (non-WAV rows) | `screenshot`, `gaps-lite`, `TBD`, empty |
| 16 | `warnings` | string | yes | comma-joined, free-form |

## Row identity

The unique key per row is the tuple
`(publication, chapter, gram_id, topic_type, sequence)`.

`topic_filename` is derived from `(publication, chapter, gram_id)` —
**not** from the full row key — and is therefore shared by every row
belonging to the same gram. The generator groups rows by gram and
merges them into one DITA topic per `topic_filename`; the trailing
columns (`topic_type`, `sequence`) determine *which block* a row
contributes to inside that topic.

## Row construction rules

1. A gram with `N` GLC links and one analysis PNG produces `N + 1` rows.
2. Analysis rows: `topic_type="analysis"`, `sequence="1"`,
   `display_text=""`, `glc_path=""`, `time_end=""`, `freq_end=""`.
3. GLC rows: `topic_type="glc"`, `sequence="1..N"` in PPTX order.
4. WAV-targeted links produce a GLC-typed row with empty `glc_path`,
   empty `time_end`/`freq_end`, the raw `.wav` URI stored in `link_href`,
   the resolved (image-root-relative) `.wav` path stored in `png_path`
   so the generator can copy it without further path arithmetic, and
   `wav_treatment` left empty for the author to fill in. `display_text`
   carries the visible link label, never the URL.
5. Warnings accumulate in column order: GLC parse warnings first, then
   path-resolution warnings, then shape warnings, then
   analysis-sheet-normalisation warnings (from FR-023).
6. Analysis rows carry both `png_path` and `analysis_docx_path` after
   FR-023 normalisation runs over the gram folder. Either column may be
   empty when the renderer was unavailable or failed; the `warnings`
   column records which direction failed
   (`"analysis renderer failed: docx→png"` or
   `"analysis renderer failed: png→docx"`). Non-analysis rows always
   leave `analysis_docx_path` empty.

## Round-trip invariant

```python
read(csv) → list[CsvRow]  # via csv.DictReader
write(list[CsvRow]) → csv  # via csv.DictWriter
```

Reading then writing a clean (warnings-free) CSV produces a file
byte-identical to the input. Trailing whitespace inside fields is
preserved; the writer never normalises numerics.

## Worked examples

### Single-gram, two GLC links, one analysis PNG

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,analysis_docx_path,wav_treatment,warnings
main,Nordic Fishing Vessels,Gram 12,Nordik Jockey,glc,1,gram_12.dita,LOFAR 1,supporting/gram12/config_1.glc,supporting/gram12/config_1.glc,271,400,images/gram12.png,,,
main,Nordic Fishing Vessels,Gram 12,Nordik Jockey,glc,2,gram_12.dita,LOFAR 2,supporting/gram12/config_2.glc,supporting/gram12/config_2.glc,180,400,images/gram12.png,,,
main,Nordic Fishing Vessels,Gram 12,Nordik Jockey,analysis,1,gram_12.dita,,,,,,Gram 12/Analysis.png,Gram 12/Analysis Sheet.docx,,
```

All three rows share `topic_filename=gram_12.dita`; the generator merges
them into one DITA topic with one analysis section followed by two
GramFrame tables.

### Progress-test gram with a missing GLC

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,analysis_docx_path,wav_treatment,warnings
progress-test-1,,Gram 03,,glc,1,gram_03.dita,LOFAR 1,supporting/gram03/config.glc,supporting/gram03/config.glc,,,images/gram03.png,,,"GLC not found"
progress-test-1,,Gram 03,,analysis,1,gram_03.dita,,,,,,Gram 03/Analysis.png,Gram 03/Analysis Sheet.docx,,
```

### WAV row awaiting author treatment

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,analysis_docx_path,wav_treatment,warnings
main,Arctic Survey,Gram 05,Arctic Surveyor,glc,1,gram_05_lofar1.dita,Audio sample,supporting/gram05/audio_clip.wav,,,,,,,,"WAV link; treatment required"
```

### Analysis row whose docx→png render failed

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,analysis_docx_path,wav_treatment,warnings
main,Nordic Fishing Vessels,Gram 17,,analysis,1,gram_17_analysis.dita,,,,,,,Gram 17/Analysis Sheet.docx,,"analysis renderer failed: docx→png"
```

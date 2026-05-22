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
| 3 | `gram_id` | string | no | canonical form is a plain integer string (`"5"`, `"12"`, `"123"`). The extractor always writes the canonical form. The generator also accepts legacy `"Gram NN"` / `"gram 5"` / `"Gram-7"` variants on read and folds them to the integer form, so an older CSV upgrades transparently. The integer form is the affordance for the CSV's refactoring role — to move a gram into a chapter that already holds the same number, the author just types the new integer in the cell. The on-disk DITA path is always built zero-padded (`gram-05/gram_05.dita`) regardless of the CSV cell's form. |
| 4 | `vessel_name` | string | yes | instructor-only content |
| 5 | `topic_type` | enum | no | `glc` or `analysis` |
| 6 | `sequence` | string | no | `1`-based per gram, scoped per `topic_type` |
| 7 | `topic_filename` | string | no | `gram_NN.dita`; identical across every row that belongs to the same gram (CSV's N+1 rows per gram collapse into one DITA topic — see `dita-topic-schema.md` §1) |
| 8 | `display_text` | string | yes (analysis rows) | human-readable link label from the PPTX run |
| 9 | `link_href` | string | yes (analysis rows) | raw hyperlink URI from the PPTX `Lofar` run. In the real corpus this is **always** a `.glc` path; the `.glc`-target invariant is documented in `high-level-spec.md` §1.5 and the reverse-spec. Any non-`.glc` value here represents a future or anomalous case (see backlog item 007). |
| 10 | `glc_path` | string | yes (analysis rows; empty for non-GLC links) | resolved `.glc` path relative to source folder. Equals `link_href` for the normal case; empty only when `link_href` is non-`.glc` (anomaly). |
| 11 | `time_end` | string | yes (when GLC missing or analysis row) | numeric string, no units |
| 12 | `freq_end` | string | yes (when GLC missing or analysis row) | numeric string, no units |
| 13 | `png_path` | string | yes | path of the asset to copy next to the topic, resolved relative to `--image-root`. For GLC rows it is the file named by the `.glc`'s inner `<data_source><filename>` element — a `.png` (~82% of grams) or `.jpg` for a pre-rendered spectrogram, or a `.wav` (~18%) when the `.glc` configures the on-PC viewer to render live from audio. The downstream generator dispatches on the extension (see `dita-topic-schema.md` §1.2/§1.3): image extensions embed inline; `.wav` triggers the GLC-viewer-link branch which copies the `.glc` + `.wav` pair side-by-side. For analysis rows it is the gram folder's `Analysis.png` after FR-023 normalisation. May be empty when the asset is missing or the renderer failed. |
| 14 | `file_size` | string | yes | decimal byte count of the file at `png_path`, captured during extraction (`Path.stat().st_size`). Populated whenever `png_path` resolves to an on-disk file (both GLC and analysis rows). Empty when `png_path` is empty or unresolvable. Surfaces duplicate assets across publications during human review — two rows pointing at byte-identical files share a `file_size`, regardless of any naming drift. The generator does not consume it; the author uses it to spot duplicate grams before signing off the CSV (delete the duplicate rows, or clear `topic_filename` to mark "do not process"). |
| 15 | `analysis_docx_path` | string | yes (non-analysis rows; analysis rows when renderer failed) | resolved relative to `--image-root`; populated for analysis rows from the gram folder's `Analysis Sheet.docx` after FR-023 normalisation. Carried for the author's review trail; the generator does not consume it. |
| 16 | `wav_treatment` | enum | yes | **Deprecated.** Originally collected an author decision (`screenshot` / `gaps-lite` / `TBD`) for rows whose GLC referenced a `.wav`. The current contract dispatches purely on `png_path`'s extension (`dita-topic-schema.md` §1) so no author decision is required; the column is retained only so older CSVs round-trip cleanly. The extractor leaves it empty and the generator ignores it. |
| 17 | `warnings` | string | yes | comma-joined, free-form |

## Row identity

The unique key per row is the tuple
`(publication, chapter, gram_id, topic_type, sequence)`.

`topic_filename` is derived from `(publication, chapter, gram_id)` —
**not** from the full row key — and is therefore shared by every row
belonging to the same gram. The generator groups rows by gram and
merges them into one DITA topic per `topic_filename`; the trailing
columns (`topic_type`, `sequence`) determine *which block* a row
contributes to inside that topic.

`generate_dita.py` enforces this tuple's uniqueness before emitting
anything: a duplicate row identity aborts the run with an error
pinpointing both colliding CSV lines. This catches the common
refactoring mistake of moving a gram into a chapter that already
holds a gram with the same `gram_id` without renumbering one of them.

## Row construction rules

1. A gram with `N` GLC links and one analysis PNG produces `N + 1` rows.
2. Analysis rows: `topic_type="analysis"`, `sequence="1"`,
   `display_text=""`, `glc_path=""`, `time_end=""`, `freq_end=""`.
3. GLC rows: `topic_type="glc"`, `sequence="1..N"` in PPTX order.
4. GLC rows whose inner `data_source/filename` is a `.wav` (the
   `.glc` configures the on-PC GLC viewer to render a fresh
   spectrogram from audio rather than reference a pre-rendered
   screenshot) keep all normal GLC-row fields populated — `glc_path`
   resolved as usual, `time_end`/`freq_end` parsed from the `.glc`,
   and `png_path` carrying the resolved `.wav` path. No author
   intervention is required; the generator emits a §1.3 GLC-viewer
   link block automatically and copies both the `.glc` and the
   companion `.wav` into the per-gram folder. `display_text` carries
   the visible link label (`"Lofar 1"`, `"Lofar 2"`, etc.), never the
   URL.
   *Note:* in the audited corpus every `Lofar` text-run hyperlink
   targets a `.glc`; the historical "WAV-targeted link" case (a
   hyperlink whose target ends in `.wav`) has not been observed in
   real data and is captured as backlog item 007.
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
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,file_size,analysis_docx_path,wav_treatment,warnings
main,Nordic Fishing Vessels,12,Nordik Jockey,glc,1,gram_12.dita,LOFAR 1,supporting/gram12/config_1.glc,supporting/gram12/config_1.glc,271,400,images/gram12.png,18432,,,
main,Nordic Fishing Vessels,12,Nordik Jockey,glc,2,gram_12.dita,LOFAR 2,supporting/gram12/config_2.glc,supporting/gram12/config_2.glc,180,400,images/gram12.png,18432,,,
main,Nordic Fishing Vessels,12,Nordik Jockey,analysis,1,gram_12.dita,,,,,,Gram 12/Analysis.png,9216,Gram 12/Analysis Sheet.docx,,
```

All three rows share `topic_filename=gram_12.dita`; the generator merges
them into one DITA topic with one analysis section followed by two
GramFrame tables.

### Progress-test gram with a missing GLC

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,file_size,analysis_docx_path,wav_treatment,warnings
progress-test-1,,3,,glc,1,gram_03.dita,LOFAR 1,supporting/gram03/config.glc,supporting/gram03/config.glc,,,images/gram03.png,,,,"GLC not found"
progress-test-1,,3,,analysis,1,gram_03.dita,,,,,,Gram 03/Analysis.png,9216,Gram 03/Analysis Sheet.docx,,
```

### GLC whose inner `data_source/filename` is `.wav` — GLC-viewer link

The `.glc` configures the on-PC GLC viewer to render a fresh
spectrogram from the named `.wav`. All normal GLC fields are
populated; `png_path` carries the resolved `.wav` path. No
`wav_treatment` is needed — the generator dispatches on the
extension and emits a §1.3 GLC-viewer link block, copying both
the `.glc` and the `.wav` next to the topic.

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,file_size,analysis_docx_path,wav_treatment,warnings
main,Arctic Survey,5,Arctic Surveyor,glc,1,gram_05.dita,Lofar 1,supporting/gram05/config_1.glc,supporting/gram05/config_1.glc,180,400,supporting/gram05/audio_clip.wav,808,,,
```

### Analysis row whose docx→png render failed

```csv
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,file_size,analysis_docx_path,wav_treatment,warnings
main,Nordic Fishing Vessels,17,,analysis,1,gram_17.dita,,,,,,,,Gram 17/Analysis Sheet.docx,,"analysis renderer failed: docx→png"
```

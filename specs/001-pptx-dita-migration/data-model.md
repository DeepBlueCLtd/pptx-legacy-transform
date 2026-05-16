# Phase 1 Data Model: PPTX to DITA Migration Pipeline

**Feature**: PPTX to DITA Migration Pipeline
**Date**: 2026-05-08

The pipeline has no database. Its data model is a chain of file-shaped
artefacts, each consumed by the next stage, plus a small set of in-memory
record types used inside the Python scripts. This document defines those
records, the relationships between them, and the validation rules each
must satisfy.

---

## 1. Source-side records (parsed from PPTX + GLC)

### 1.1 `SourcePresentation`

A single instructor PPTX file rooted somewhere under the configurable
content root.

| Field | Type | Source | Notes |
|---|---|---|---|
| `path` | `pathlib.Path` | filesystem walk | absolute path |
| `publication` | `str` | filename pattern (R2) | `"main"` or `"progress-test-N"` |
| `chapter` | `str \| None` | parent folder name (R3) | `None` for progress tests |
| `chapter_slug` | `str \| None` | slugified chapter | folder-safe; `None` for progress tests |
| `slides` | `list[Slide]` | `python-pptx` | excludes the welcome slide |

**Validation**: `path` must exist and end in `.pptx`. If `publication`
matches the test pattern, `chapter` is `None` and any chapter-derived
output uses publication-only paths.

### 1.2 `Slide`

A single content slide (welcome slide is filtered out before this record
is built).

| Field | Type | Source | Notes |
|---|---|---|---|
| `slide_number` | `int` | `python-pptx` slide index (1-based) | matches user-facing numbering |
| `shapes` | `list[Shape]` | `python-pptx` | flattened, group shapes expanded |

**Validation**: `slide_number >= 2` (welcome is slide 1). A slide whose
shape count deviates significantly from the expected count for a 15-gram
layout is *flagged*, not rejected.

### 1.3 `Shape`

A single shape on a slide. Both the introspector and the (eventual)
extractor walk these.

| Field | Type | Source | Notes |
|---|---|---|---|
| `index` | `int` | enumerate over slide shapes | 0-based |
| `name` | `str` | `shape.name` | e.g. `"Rectangle 12"` |
| `shape_type` | `str` | `shape.shape_type` repr | enum-like, may be `None` for placeholders |
| `left_in`, `top_in`, `width_in`, `height_in` | `float` | EMU → inches (rounded 2dp) | for human report |
| `text` | `str` | `shape.text_frame.text` | empty for non-text shapes |
| `shape_hyperlink` | `str \| None` | XML lookup (R4) | shape-level click action target |
| `runs` | `list[Run]` | text frame walk | empty for non-text shapes |

**Validation**: Either `shape_hyperlink` is `None` or it is a non-empty
string. Truncation to 80 chars happens at *report* time, not on the
record itself.

### 1.4 `Run`

A single text run inside a shape's text frame.

| Field | Type | Source | Notes |
|---|---|---|---|
| `text` | `str` | `run.text` | preserves whitespace |
| `run_hyperlink` | `str \| None` | XML lookup (R4) | text-run-level target |

### 1.5 `GramPlaceholder` *(produced by the deferred shape-grouping stub)*

A logical unit that the extractor's `extract_grams_from_slide()` returns
once implemented. Until implemented, this record exists only as a
docstring contract on the stub.

| Field | Type | Notes |
|---|---|---|
| `gram_id` | `str` | e.g. `"Gram 12"` |
| `vessel_name` | `str` | may be empty |
| `png_href` | `str \| None` | hyperlink target on title shape |
| `glc_links` | `list[GlcLink]` | ordered as found in the link text box |

### 1.6 `GlcLink`

| Field | Type | Notes |
|---|---|---|
| `display_text` | `str` | e.g. `"LOFAR 1"` |
| `href` | `str` | relative URI from the run's hyperlink, may be `.glc` or `.wav` |

### 1.7 `AnalysisSheet` *(produced by the FR-023 normalisation stage)*

The analysis artefact attached to a gram *folder* on disk. Exactly one
record per gram folder regardless of how many slide instances reference
that gram.

| Field | Type | Source | Notes |
|---|---|---|---|
| `gram_folder` | `pathlib.Path` | filesystem | e.g. `Gram 12/` |
| `docx_path` | `pathlib.Path \| None` | filesystem | `Gram NN/Analysis Sheet.docx`; populated after normalisation unless renderer failed |
| `png_path` | `pathlib.Path \| None` | filesystem | `Gram NN/Analysis.png`; populated after normalisation unless renderer failed |
| `source_form` | `str` | enum: `"docx"`, `"png"`, `"both"`, `"missing"` | which form(s) existed *before* normalisation; recorded for the CSV review trail |
| `warnings` | `list[str]` | accumulated during normalisation | empty when both forms exist post-normalisation |

**Validation**: The normalisation stage produces one record per gram
folder it visits; a `"missing"` `source_form` (no `.docx` and no `.png`
present) yields a warning and leaves both paths `None`. A renderer
failure leaves the *unproduced* path `None` and records a warning; the
*present* path remains populated. The stage MUST NOT raise on renderer
unavailability — the run continues and the affected gram's analysis row
surfaces the warning in the CSV.

### 1.8 `GlcDocument` *(produced by `parse_glc`)*

The narrow projection of a GLC XML file used by the pipeline. Per R6,
the parser is tolerant: missing fields produce empty strings plus
warnings.

| Field | Type | Source XPath | Notes |
|---|---|---|---|
| `time_end` | `str` | `data_source/bitmap_crop_values/bottom_crop` | numeric string; may be empty |
| `freq_end` | `str` | `settings/lofar/bandwidth` | numeric string; may be empty |
| `image_filename` | `str` | `data_source/filename` (path stripped) | bare filename only |
| `warnings` | `list[str]` | accumulated during parse | empty if clean |

**Validation**: All four fields are always populated (with empty strings
or empty list as the "no value" sentinel). The parser never raises.

---

## 2. Intermediate-side record: `CsvRow`

The intermediate CSV produced by Stage 2 and consumed by Stage 4 has one
row per resulting DITA topic. The unique key per row is
`(publication, chapter, gram_id, topic_type, sequence)`.

| Column | Type | Source | Validation |
|---|---|---|---|
| `publication` | `str` | from `SourcePresentation` | `"main"` or `"progress-test-N"`; non-empty |
| `chapter` | `str` | folder-derived; empty for tests | empty *only* when publication is a test |
| `gram_id` | `str` | from `GramPlaceholder` | format `"Gram NN"` (warned otherwise) |
| `vessel_name` | `str` | from `GramPlaceholder` | may be empty (warns at WARNING level) |
| `topic_type` | `str` | enum: `"glc"` or `"analysis"` | must be one of the two |
| `sequence` | `str` | `1`-based per gram, type-scoped | `"1"` for analysis rows; `"1..N"` for glc rows |
| `topic_filename` | `str` | computed | matches `gram_xx.dita`; identical across all rows belonging to the same gram (the CSV's N+1 rows collapse into one DITA topic) |
| `display_text` | `str` | from `GlcLink.display_text` | human-readable link label; empty for analysis rows |
| `link_href` | `str` | from `GlcLink.href` | raw hyperlink URI; in the audited corpus always a `.glc`; empty for analysis rows |
| `glc_path` | `str` | resolved relative to source folder | empty for analysis rows |
| `time_end` | `str` | from `GlcDocument.time_end` | empty for analysis rows |
| `freq_end` | `str` | from `GlcDocument.freq_end` | empty for analysis rows |
| `png_path` | `str` | resolved relative to source folder; sourced from `GlcDocument.image_filename` for glc rows and from `AnalysisSheet.png_path` for analysis rows | for glc rows: the asset named inside the `.glc` — `.png`/`.jpg` triggers inline embedding, `.wav` triggers the GLC-viewer-link branch (see `dita-topic-schema.md` §1.2/§1.3); for analysis rows: populated post-FR-023 unless renderer failed |
| `analysis_docx_path` | `str` | resolved relative to source folder; sourced from `AnalysisSheet.docx_path` | empty for glc rows; populated for analysis rows post-FR-023 unless renderer failed |
| `wav_treatment` | `str` | (deprecated) | retained for round-trip compatibility only; extractor leaves it empty and generator ignores it (see `csv-schema.md` column 15) |
| `warnings` | `str` | comma-joined warning list | empty if clean |

**Row-construction rules**:

1. A gram with N GLC links and one analysis PNG produces `N + 1` rows.
2. Analysis rows always have `sequence = "1"` (one analysis per gram by
   construction).
3. GLC rows are numbered by their order of appearance in the link text
   box, starting at `1`.
4. A GLC row's downstream rendering is selected by the extension of
   `png_path` (the asset named inside the `.glc`): `.png`/`.jpg`
   produces a §1.2 GramFrame table with the image embedded; `.wav`
   produces a §1.3 GLC-viewer link block. The historical
   `wav_treatment` author-decision workflow is retired.
5. The warnings column accumulates *all* recoverable issues for the row,
   joined by `", "`.
6. Analysis rows carry both `png_path` and `analysis_docx_path`
   populated after FR-023 normalisation. Either may be empty (with a
   `warnings` entry such as `"analysis renderer failed: docx→png"` or
   `"analysis renderer failed: png→docx"`) when the renderer was
   unavailable or failed for that gram folder. The DITA generator
   continues to consume `png_path` only — `analysis_docx_path` is
   carried for the technical author's review trail and is not required
   by the generator.

**Encoding**: UTF-8 with BOM, CRLF line endings (R11). Excel-friendly.

**Round-trip invariant**: `Read(csv) → CsvRow → Write(csv)` is the
identity for any clean row (same field values in same order).

---

## 3. Output-side records (DITA topics + ditamaps)

### 3.1 `DitaTopic`

The generator writes one topic per gram (`gram_NN.dita`) as a
standalone XML file with no DTD declaration and no XML preamble
beyond the encoding line. The CSV's N+1 rows for a gram (one
`topic_type=analysis` row plus N `topic_type=glc` rows) all share
the same `topic_filename` and collapse into one topic; the generator
groups by `(publication, chapter, gram_id)` before emitting.

Filenames and folder placement come from the CSV row's
`publication`/`chapter`/`topic_filename`. See
[`contracts/gramframe.md`](contracts/gramframe.md) for the rendered-HTML
contract the `gram-config` block must satisfy.

#### 3.1.1 `gram_xx.dita` — per-gram topic

Required structure:

```xml
<topic id="gram_NN">
  <title>Gram NN<ph audience="-trainee"> - {vessel_name}</ph></title>
  <body>
    <!-- 1. Analysis-sheet section, from the topic_type=analysis row -->
    <section audience="-trainee">
      <title>Analysis Sheet</title>
      <!-- PNG: <image href="{slug}.png" placement="break" align="center"/> -->
      <!-- DOCX: <p><xref href="{slug}.docx" format="docx" scope="local">Analysis Sheet</xref></p> -->
    </section>

    <!-- 2. One GramFrame block per topic_type=glc row, in sequence order -->
    <section>
      <table outputclass="gram-config">
        <tgroup cols="2">
          <colspec colname="c1" colnum="1"/>
          <colspec colname="c2" colnum="2"/>
          <tbody>
            <row>
              <entry namest="c1" nameend="c2">
                <image href="{slug}.png" placement="break" align="center"/>
              </entry>
            </row>
            <row><entry>time-start</entry><entry>0</entry></row>
            <row><entry>time-end</entry><entry>{time_end}</entry></row>
            <row><entry>freq-start</entry><entry>0</entry></row>
            <row><entry>freq-end</entry><entry>{freq_end}</entry></row>
          </tbody>
        </tgroup>
      </table>
    </section>

    <!-- 3. GLC-viewer link block — emitted instead of (2) when the GLC's
         inner data_source/filename is a .wav rather than an image.
         Both the .glc and its companion .wav are copied alongside the
         topic; the on-PC GLC viewer reads the .glc and resolves the .wav
         next to it. See dita-topic-schema.md §1.3. -->
    <section>
      <p><xref href="{slug}.glc" format="glc" scope="local">{display_text}</xref></p>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

Validation:

- `id` is the `topic_filename` minus the `.dita` extension
  (e.g. `gram_12`).
- The analysis section is omitted when the gram has no
  `topic_type=analysis` row.
- The `<ph audience="-trainee">` wrapper in the title is omitted only
  when `vessel_name` is empty; otherwise it is always present.
- The analysis section always carries `audience="-trainee"`.
- The two named `<colspec>` elements inside each `gram-config` table
  are required so DITA-OT emits `colspan="2"` on the image row; without
  them the GramFrame bundle rejects the table.
- `time-start` and `freq-start` are always literal `"0"` (per
  spec section 1.6).

### 3.2 `Ditamap`

One ditamap per publication, written under `output/ditamaps/`.

#### 3.2.1 Main ditamap (`main.ditamap`)

Required structure:

```xml
<map title="Main">
  <topichead navtitle="{Chapter Title}">
    <topicref href="main/{chapter-slug}/gram-NN/gram_NN.dita"/>
    ...
  </topichead>
  ...
</map>
```

One `topicref` per gram (not per CSV row); the analysis row's
contribution lives inside the same `gram_NN.dita` as an instructor-only
section. Chapters are emitted in the order of first appearance in the
CSV (which is, by R3, alphabetical folder order).

#### 3.2.2 Test ditamap (`progress-test-N.ditamap`)

Required structure:

```xml
<map title="Progress Test N">
  <topicref href="progress-test-N/gram-NN/gram_NN.dita"/>
  ...
</map>
```

Flat — no `<topichead>` elements (FR-012, section 1.11).

### 3.3 `OutputManifest` (`manifest.txt`)

Plain-text file written at the root of the output tree per R9.

```
output/main/nordic-fishing-vessels/gram_12_lofar1.dita
output/main/nordic-fishing-vessels/gram_12_lofar2.dita
output/main/nordic-fishing-vessels/gram_12_analysis.dita
output/ditamaps/main.ditamap
...
```

One file per line, sorted, relative to the output directory. The
generator overwrites this on every run.

### 3.4 `SkippedReport` (`skipped.txt`)

Plain-text file produced when at least one row is skipped (per R8 / FR-011).

```
publication=main chapter=nordic-fishing-vessels gram_id="Gram 05" topic_type=glc sequence=1 reason="png_path missing"
...
```

One line per skipped row, with stable ordering (CSV row order).

---

## 4. Relationships

```
SourcePresentation 1───* Slide 1───* Shape 1───* Run
                              │
                              └── (via shape-grouping stub) ───*
                                          GramPlaceholder 1───* GlcLink
                                                  │
                                                  ├── 1 analysis-sheet hyperlink (→ AnalysisSheet)
                                                  └── 0..* GLC files (parsed → GlcDocument)

GramFolder        ──> AnalysisSheet  (1-1, produced by FR-023 normalisation)
GramPlaceholder   ──> CsvRow*        (one per GLC link + one analysis row;
                                      the analysis row's png_path and
                                      analysis_docx_path are sourced from
                                      the gram folder's AnalysisSheet)
CsvRow            ──> DitaTopic
{CsvRow per publication} ──> Ditamap
{CsvRow that is skipped} ──> SkippedReport entry
{DitaTopic, Ditamap}    ──> OutputManifest entry
```

---

## 5. State transitions

The pipeline has no long-lived state. The only state change of interest
is the technical author editing the CSV between Stages 2 and 4. The
contract for that edit:

| Field | Author may edit? | Notes |
|---|---|---|
| `publication`, `chapter`, `gram_id` | No | identity of the row |
| `topic_type`, `sequence`, `topic_filename` | No | derived; changes break ditamap consistency |
| `vessel_name` | Yes | typos and missing names |
| `display_text` | Yes | rare |
| `link_href` | Yes | rare — only to correct an extractor mis-read |
| `glc_path`, `png_path`, `analysis_docx_path` | Yes | to fix unresolved paths or re-point to a manually produced asset |
| `time_end`, `freq_end` | Yes | to override broken GLC parses |
| `wav_treatment` | Yes | required where it is empty |
| `warnings` | Yes (clear after fix) | author marks rows handled |

The generator does *not* enforce any of these by hash-checking the CSV;
it trusts the author's signed-off file. The README warns about the
identity columns explicitly.

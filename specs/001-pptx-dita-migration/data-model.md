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

### 1.7 `GlcDocument` *(produced by `parse_glc`)*

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
| `topic_filename` | `str` | computed | matches `gram_xx_lofarN.dita` or `gram_xx_analysis.dita` |
| `display_text` | `str` | from `GlcLink.display_text` | human-readable link label; empty for analysis rows |
| `link_href` | `str` | from `GlcLink.href` | raw hyperlink URI; source of truth for WAV detection and stub `xref href`; empty for analysis rows |
| `glc_path` | `str` | resolved relative to source folder | empty for analysis rows and for WAV-targeted rows |
| `time_end` | `str` | from `GlcDocument.time_end` | empty for analysis rows |
| `freq_end` | `str` | from `GlcDocument.freq_end` | empty for analysis rows |
| `png_path` | `str` | resolved relative to source folder | empty for glc rows whose link target was a .glc |
| `wav_treatment` | `str` | author-supplied | empty unless link was .wav; values: `screenshot`, `gaps-lite`, `TBD`, empty |
| `warnings` | `str` | comma-joined warning list | empty if clean |

**Row-construction rules**:

1. A gram with N GLC links and one analysis PNG produces `N + 1` rows.
2. Analysis rows always have `sequence = "1"` (one analysis per gram by
   construction).
3. GLC rows are numbered by their order of appearance in the link text
   box, starting at `1`.
4. WAV-targeted links produce a row whose `topic_type` is `"glc"` and
   whose `wav_treatment` is left for the technical author to fill in.
   `glc_path` is empty for such rows; the raw `.wav` URI lives in
   `link_href` (source of truth for the generator's WAV branching and
   stub `xref href`), and `display_text` carries the visible link label
   exactly as it appeared in the PPTX run.
5. The warnings column accumulates *all* recoverable issues for the row,
   joined by `", "`.

**Encoding**: UTF-8 with BOM, CRLF line endings (R11). Excel-friendly.

**Round-trip invariant**: `Read(csv) → CsvRow → Write(csv)` is the
identity for any clean row (same field values in same order).

---

## 3. Output-side records (DITA topics + ditamaps)

### 3.1 `DitaTopic`

The generator writes two flavours of topic, both as standalone XML
files, no DTD declaration, no XML preamble beyond the encoding line.
Filenames and folder placement come from the CSV row's
`publication`/`chapter`/`topic_filename`.

#### 3.1.1 `gram_xx_lofarN.dita` (from a GLC row)

Required structure:

```xml
<topic id="gram_NN_lofarM">
  <title>Gram NN<ph audience="-trainee"> - {vessel_name}</ph></title>
  <body>
    <section>
      <table outputclass="gram-config">
        <tgroup cols="2">
          <tbody>
            <row>
              <entry namest="c1" nameend="c2">
                <image href="{png_path resolved against image-root}"
                       placement="break" align="center"/>
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
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

Validation:

- `id` is the `topic_filename` minus the `.dita` extension.
- The `<ph audience="-trainee">` wrapper is omitted only when
  `vessel_name` is empty; otherwise it is always present.
- `time-start` and `freq-start` are always literal `"0"` (per
  spec section 1.6).

#### 3.1.2 `gram_xx_analysis.dita` (from an analysis row)

Required structure:

```xml
<topic id="gram_NN_analysis" audience="-trainee">
  <title>Gram NN Analysis</title>
  <body>
    <section>
      <image href="{png_path resolved against image-root}"
             placement="break" align="center"/>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

Validation: `audience="-trainee"` is always set on the root topic.

#### 3.1.3 WAV stub topic (from a `wav_treatment="gaps-lite"` row)

Required structure:

```xml
<!-- MANUAL REVIEW: GAPS-Lite required -->
<topic id="gram_NN_lofarM">
  <title>Gram NN<ph audience="-trainee"> - {vessel_name}</ph></title>
  <body>
    <section>
      <note>This gram requires GAPS-Lite playback.</note>
      <p><xref href="{wav target}" format="wav" scope="external">{display_text}</xref></p>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

### 3.2 `Ditamap`

One ditamap per publication, written under `output/ditamaps/`.

#### 3.2.1 Main ditamap (`main.ditamap`)

Required structure:

```xml
<map title="Main">
  <topichead navtitle="{Chapter Title}">
    <topicref href="../main/{chapter-slug}/gram_NN_lofarM.dita"/>
    <topicref href="../main/{chapter-slug}/gram_NN_analysis.dita"/>
    ...
  </topichead>
  ...
</map>
```

Chapters are emitted in the order of first appearance in the CSV (which
is, by R3, alphabetical folder order).

#### 3.2.2 Test ditamap (`progress-test-N.ditamap`)

Required structure:

```xml
<map title="Progress Test N">
  <topicref href="../progress-test-N/gram_NN_lofarM.dita"/>
  <topicref href="../progress-test-N/gram_NN_analysis.dita"/>
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
publication=main chapter=nordic-fishing-vessels gram_id="Gram 05" topic_type=glc sequence=1 reason="wav_treatment is TBD"
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
                                                  ├── 1 PNG hyperlink (analysis)
                                                  └── 0..* GLC files (parsed → GlcDocument)

GramPlaceholder ──> CsvRow*  (one per GLC link + one for analysis PNG)
CsvRow          ──> DitaTopic
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
| `glc_path`, `png_path` | Yes | to fix unresolved paths |
| `time_end`, `freq_end` | Yes | to override broken GLC parses |
| `wav_treatment` | Yes | required where it is empty |
| `warnings` | Yes (clear after fix) | author marks rows handled |

The generator does *not* enforce any of these by hash-checking the CSV;
it trusts the author's signed-off file. The README warns about the
identity columns explicitly.

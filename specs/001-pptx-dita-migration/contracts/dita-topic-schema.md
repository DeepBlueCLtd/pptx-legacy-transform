# DITA Output Schema

The generator's contract is to produce DITA topics and ditamaps that
slot into the existing pub-9/pub-10 publishing toolchain unchanged.
This document fixes the exact shape of the generated XML so a future
maintainer (and the test suite) can verify each topic without referring
back to the source spec.

All output files are:

- UTF-8 encoded, no BOM
- LF line endings (`"\n"`) — the publishing toolchain on Linux build
  machines is happier with LF than CRLF
- No XML declaration (matches existing pub-9/pub-10 convention)
- No DOCTYPE declaration (validation against the DITA DTD happens in
  Oxygen at publish time)

## 1. `gram_NN_lofarM.dita` — gram-config topic

Produced for every CSV row with `topic_type="glc"` (excluding skipped
WAV rows).

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
                <image href="{image_href}" placement="break" align="center"/>
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

Substitutions:

| Placeholder | Source |
|---|---|
| `NN` | `gram_id` numeric portion (zero-padded as it appears) |
| `M` | `sequence` |
| `vessel_name` | CSV column; if empty, the entire `<ph>` element is omitted |
| `image_href` | `png_path` resolved against `--image-root`, expressed relative to the topic's directory |
| `time_end` | CSV column; if empty, literal `""` is written |
| `freq_end` | CSV column; if empty, literal `""` is written |

## 2. `gram_NN_analysis.dita` — instructor-only analysis topic

Produced for every CSV row with `topic_type="analysis"`.

```xml
<topic id="gram_NN_analysis" audience="-trainee">
  <title>Gram NN Analysis</title>
  <body>
    <section>
      <image href="{image_href}" placement="break" align="center"/>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

Note: the `audience="-trainee"` attribute is on the root topic. The
trainee profile excludes this topic entirely; the instructor profile
includes it.

## 3. WAV stub topic (`wav_treatment="gaps-lite"`)

Produced for every CSV row whose `wav_treatment` is `gaps-lite`.

```xml
<!-- MANUAL REVIEW: GAPS-Lite required -->
<topic id="gram_NN_lofarM">
  <title>Gram NN<ph audience="-trainee"> - {vessel_name}</ph></title>
  <body>
    <section>
      <note>This gram requires GAPS-Lite playback.</note>
      <p><xref href="{wav_href}" format="wav" scope="external">{display_text}</xref></p>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

`wav_href` is taken from the row's `link_href` column when `glc_path` is
empty and `link_href` ends in `.wav`; the `<xref>` element's visible
text comes from `display_text`. The extractor never conflates the two:
`display_text` is the human-readable label exactly as it appeared in
the PPTX run; `link_href` is the raw URI. (See R8 and the WAV-row rule
in `csv-schema.md`.)

## 4. WAV row with `wav_treatment="screenshot"`

Treated identically to a normal GLC row: the generator emits the
gram-config topic shape from §1 using the row's `png_path`,
`time_end`, and `freq_end` columns. The technical author is
responsible for filling those columns when choosing `screenshot`.

## 5. Skipped rows

Rows with `wav_treatment="TBD"`, empty `wav_treatment` on a WAV-typed
row, or any unknown `wav_treatment` are *not* emitted as DITA. They
are recorded one-per-line in `skipped.txt`:

```
publication=main chapter=arctic-survey gram_id="Gram 05" topic_type=glc sequence=1 reason="wav_treatment is TBD"
```

## 6. Ditamaps

### 6.1 Main ditamap (`ditamaps/main.ditamap`)

```xml
<map title="Main">
  <topichead navtitle="{Chapter Title}">
    <topicref href="../main/{chapter-slug}/gram_NN_lofarM.dita"/>
    <topicref href="../main/{chapter-slug}/gram_NN_analysis.dita"/>
    <!-- ...all topics for this chapter, in CSV row order... -->
  </topichead>
  <!-- ...further chapters in alphabetical folder order... -->
</map>
```

Notes:

- `topicref` URLs are relative to the ditamap's directory, hence the
  `..` prefix.
- Analysis topicrefs are emitted alongside the GLC topicrefs for the
  same gram; the trainee profile elides the analysis topic via the
  topic-level `audience` attribute set in §2.
- `topichead` `navtitle` is the human-readable chapter title (mixed
  case), distinct from the chapter slug used in URLs.

### 6.2 Test ditamap (`ditamaps/progress-test-N.ditamap`)

```xml
<map title="Progress Test N">
  <topicref href="../progress-test-N/gram_NN_lofarM.dita"/>
  <topicref href="../progress-test-N/gram_NN_analysis.dita"/>
  <!-- ...further topics, flat... -->
</map>
```

No `topichead` elements (FR-012, section 1.11 of the source spec).

## 7. Manifest (`manifest.txt`)

Plain text. One line per file produced. Sorted alphabetically.
Paths relative to `--out`. Includes ditamaps.

```
ditamaps/main.ditamap
ditamaps/progress-test-1.ditamap
main/arctic-survey/gram_01_analysis.dita
main/arctic-survey/gram_01_lofar1.dita
...
```

## 8. Filename conventions

| Topic | Filename |
|---|---|
| GLC row | `gram_NN_lofarM.dita` (e.g. `gram_12_lofar1.dita`) |
| Analysis row | `gram_NN_analysis.dita` (e.g. `gram_12_analysis.dita`) |
| Main ditamap | `main.ditamap` |
| Test ditamap | `progress-test-N.ditamap` (e.g. `progress-test-1.ditamap`) |

`NN` is the numeric portion of `gram_id` exactly as it appears in the
CSV (no padding adjustments). The expectation is that the source
material uses two-digit numbering today; if it grows past 99 the format
silently widens to three digits.

## 9. Folder layout

```
{out}/
├── main/
│   ├── {chapter-slug-1}/
│   │   ├── gram_NN_lofarM.dita
│   │   ├── gram_NN_analysis.dita
│   │   └── ...
│   └── {chapter-slug-2}/
│       └── ...
├── progress-test-1/
│   ├── gram_NN_lofarM.dita
│   └── gram_NN_analysis.dita
├── progress-test-2/
│   └── ...
├── ditamaps/
│   ├── main.ditamap
│   ├── progress-test-1.ditamap
│   └── progress-test-2.ditamap
├── manifest.txt
└── skipped.txt   (only when at least one row was skipped)
```

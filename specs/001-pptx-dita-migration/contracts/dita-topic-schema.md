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
| `image_href` | The asset is copied into the topic's per-gram folder and renamed to a slug of its source filename (see §10). The href is the bare local filename, e.g. `lofar-1.png`. |
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
      <p><xref href="{wav_href}" format="wav" scope="local">{display_text}</xref></p>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

The WAV referenced by the row's `png_path` column (with `link_href`
and `glc_path` retained as fallbacks for older CSVs) is copied into
the topic's per-gram folder and renamed to a slug of its source
filename (see §10). `wav_href` is therefore the bare local filename,
e.g. `audio-clip.wav`. The `<xref>` element's visible text comes from
`display_text`. The extractor never conflates the two: `display_text`
is the human-readable label exactly as it appeared in the PPTX run;
`link_href` is the raw URI from the PPTX hyperlink, while `png_path`
carries the asset path resolved against `--image-root` so the
generator can copy it without further path arithmetic.
`scope="local"` records that the WAV sits inside the publication, even
though the player is invoked externally via GAPS-Lite. (See R8 and the
WAV-row rule in `csv-schema.md`.)

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

### 6.1 Main ditamap (`main.ditamap`)

```xml
<map title="Main">
  <topichead navtitle="{Chapter Title}">
    <topicref href="main/{chapter-slug}/gram_NN_lofarM.dita"/>
    <topicref href="main/{chapter-slug}/gram_NN_analysis.dita"/>
    <!-- ...all topics for this chapter, in CSV row order... -->
  </topichead>
  <!-- ...further chapters in alphabetical folder order... -->
</map>
```

Notes:

- The ditamap lives at the output root next to its sibling `main/`
  folder, so `topicref` URLs are simple forward paths into that
  folder (no `../` prefix).
- Analysis topicrefs are emitted alongside the GLC topicrefs for the
  same gram; the trainee profile elides the analysis topic via the
  topic-level `audience` attribute set in §2.
- `topichead` `navtitle` is the human-readable chapter title (mixed
  case), distinct from the chapter slug used in URLs.

### 6.2 Test ditamap (`progress-test-N.ditamap`)

```xml
<map title="Progress Test N">
  <topicref href="progress-test-N/gram_NN_lofarM.dita"/>
  <topicref href="progress-test-N/gram_NN_analysis.dita"/>
  <!-- ...further topics, flat... -->
</map>
```

No `topichead` elements (FR-012, section 1.11 of the source spec).

## 7. Manifest (`manifest.txt`)

Plain text. One line per file produced. Sorted alphabetically.
Paths relative to `--out`. Includes ditamaps.

```
main.ditamap
main/arctic-survey/gram_01_analysis.dita
main/arctic-survey/gram_01_lofar1.dita
progress-test-1.ditamap
progress-test-1/gram_01_analysis.dita
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

Each gram (a single `gram_id` within a publication) lives in its own
sub-directory. The grouping mirrors the supporting-material folder
structure in the source content (one folder per gram, in the chapter
or per-publication root) so that locating an asset on disk needs no
look-up table.

```
{out}/
├── main.ditamap
├── main/
│   ├── {chapter-slug-1}/
│   │   ├── gram-NN/
│   │   │   ├── gram_NN_lofarM.dita
│   │   │   ├── {slug}.png        ← asset copied + slug-renamed (see §10)
│   │   │   ├── gram_NN_analysis.dita
│   │   │   └── {slug}.docx
│   │   └── gram-NN/
│   │       └── ...
│   └── {chapter-slug-2}/
│       └── ...
├── progress-test-1.ditamap
├── progress-test-1/
│   ├── gram-NN/
│   │   ├── gram_NN_lofarM.dita
│   │   ├── {slug}.png
│   │   └── gram_NN_analysis.dita
│   └── gram-NN/
│       └── ...
├── progress-test-2.ditamap
├── progress-test-2/
│   └── ...
├── manifest.txt
└── skipped.txt   (only when at least one row was skipped)
```

Each ditamap is paired with a similarly-named sibling content folder
at the output root. Inside a content folder, each gram (a single
`gram_id`) lives in its own `gram-NN/` sub-directory, where `NN` is
the numeric portion of `gram_id` exactly as it appears in the CSV
(zero-padded to at least two digits by the extractor; widens silently
past 99).

## 10. Asset copy and rename

The DITA-writing phase is responsible for materialising a
self-contained publication tree. For every topic that references an
external asset (PNG screenshot, WAV file, or analysis sheet), the
generator:

1. Resolves the source path as `--image-root` joined with the relevant
   CSV column. For all three topic shapes (§1, §2, §3) this is
   `png_path` — the extractor resolves the asset path against the
   image root so the generator can copy it blindly. `link_href` and
   `glc_path` are retained as fallbacks for older CSVs.
2. Copies the source file into the topic's per-gram folder (`gram-NN/`).
3. Renames the copy to a slug of the *source* filename, preserving the
   original extension lower-cased. For example, the asset referenced
   by `gram_12_lofar1.dita` whose source is `Lofar 1 ABC.PNG` is
   copied to `gram-12/lofar-1-abc.png`.
4. Uses the bare local filename as the topic's `href`. References
   never traverse out of the per-gram directory.

The per-gram folder gives each asset a unique location automatically:
two grams in the same chapter that both have a source `Lofar 1.png`
end up at `gram-NN/lofar-1.png` and `gram-MM/lofar-1.png`, with no
collision. Slugifying the filename keeps hrefs URL-safe (no spaces,
ASCII only) without losing the human-readable relationship to the
source.

Asset copies use `shutil.copy2`, which preserves the source's modification
time. Two consecutive generator runs against an unchanged source tree
therefore produce byte- and stat-identical assets, satisfying the
idempotency contract (R9).

If a referenced source file is missing, the generator logs a warning
and emits the topic with the *intended* local href anyway. This keeps
the topic XML stable across runs: dropping the asset into the source
tree at the expected path and re-running the generator resolves the
dangling reference without touching the topic file.

The manifest (`§7`) lists every file the generator writes — topics,
ditamaps, **and** copied assets — relative to `{out}`.

## 11. HTML preview (development only)

The DITA tree at `{out}` is the production deliverable, consumed by
Oxygen XML Author for publishing. For development sanity-checks, the
project ships `publish_html.py`, which renders the same tree to HTML5
using DITA-OT. The HTML output is not delivered to the air-gapped
target — Oxygen remains the production publishing path (FR-021).

`publish_html.py` operates on `{out}` non-destructively:

1. Stages a copy of `{out}` under `.dita-build/` and prepends the OASIS
   DITA Topic and Map DOCTYPE declarations (the source DITA omits
   DOCTYPEs per §0; Oxygen handles validation at publish time, but
   DITA-OT requires them to classify elements). Ditamaps already sit
   at the root of `{out}` with forward-only hrefs into their sibling
   content folders, so no path rewriting or promotion step is needed.
2. Invokes DITA-OT once per staged ditamap with
   `--format=html5 --processing-mode=lax`, writing to
   `html/{ditamap-stem}/`.
3. Removes the staging directory once publishing completes.

The script's only inputs are `--dita` (default `dita/`), `--out`
(default `html/`), and `--dita-ot` (path to a DITA-OT installation
that the maintainer transfers across the air-gap per FR-021).

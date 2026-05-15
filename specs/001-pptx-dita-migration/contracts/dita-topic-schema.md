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

## 1. `gram_NN.dita` — single gram topic

One DITA topic per gram. The body groups everything for that gram into
a single page: the instructor-only Analysis Sheet section first, then
one block per `.glc` (or WAV) link beneath the gram header in the
source PPTX, in `sequence` order.

A gram with N `.glc` links and one analysis sheet therefore produces
**one** `gram_NN.dita` file containing one analysis section plus N
GramFrame tables — not N+1 DITA topics. The CSV still carries N+1
rows per gram (one per `topic_type=glc` row and one for
`topic_type=analysis`); the generator groups them by
`(publication, chapter, gram_id)` and folds them into one topic.

```xml
<topic id="gram_NN">
  <title>Gram NN<ph audience="-trainee"> - {vessel_name}</ph></title>
  <body>
    <section audience="-trainee">       <!-- §1.1 analysis sheet -->
      <title>Analysis Sheet</title>
      <!-- one of: -->
      <image href="{slug}.png" placement="break" align="center"/>
      <p><xref href="{slug}.docx" format="docx" scope="local">Analysis Sheet</xref></p>
    </section>

    <section>                            <!-- §1.2 GramFrame, repeats per .glc -->
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

    <section>                            <!-- §1.3 GAPS-Lite stub, optional -->
      <note>This gram requires GAPS-Lite playback.</note>
      <p><xref href="{slug}.wav" format="wav" scope="local">{display_text}</xref></p>
    </section>
  </body>

  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

When any GAPS-Lite stub is present the topic file is prefixed with a
`<!-- MANUAL REVIEW: GAPS-Lite required -->` comment so the
technical author can find it later.

### 1.1 Analysis-sheet section

Built from the `topic_type="analysis"` row's `png_path` column
(populated by the extractor after FR-023 normalisation). The section
carries `audience="-trainee"` so the trainee profile elides it
entirely; only the instructor build includes the analysis sheet.

| Asset suffix | Rendering |
|---|---|
| `.png` | Embedded inline via `<image href="{slug}.png" .../>` |
| `.docx` (or any other suffix) | Linked via `<xref href="{slug}.docx" format="docx" scope="local">Analysis Sheet</xref>` |

The `slug` is the slug of the *source* filename (e.g. `Analysis Sheet.docx`
→ `analysis-sheet.docx`); see §10.

### 1.2 GramFrame table block

One `<table outputclass="gram-config">` per `topic_type="glc"` row
whose `wav_treatment` is empty (treated as a normal GLC screenshot
row) or `screenshot`. The shape is exactly what
`gramframe.bundle.js` expects after DITA-OT renders it; see
[`gramframe.md`](./gramframe.md) for the rendered-HTML contract and the
reason the two `<colspec>` elements are not optional.

Placeholders:

| Placeholder | Source |
|---|---|
| `NN` | `gram_id` numeric portion (zero-padded as it appears) |
| `vessel_name` | CSV column; if empty, the entire `<ph>` element is omitted |
| `image_href` | Slugified copy of the asset, placed in the same per-gram folder as the topic (see §10) |
| `time_end` | CSV column; if empty, literal `""` is written |
| `freq_end` | CSV column; if empty, literal `""` is written |

### 1.3 GAPS-Lite WAV stub block

One stub block per `topic_type="glc"` row with
`wav_treatment="gaps-lite"`. The WAV referenced by the row's
`png_path` column (with `link_href` and `glc_path` retained as
fallbacks for older CSVs) is copied into the per-gram folder and
slug-renamed (see §10). `scope="local"` records that the WAV sits
inside the publication, even though the player is invoked externally
via GAPS-Lite. The `<xref>` element's visible text comes from
`display_text`; the extractor never conflates the two:
`display_text` is the human-readable label exactly as it appeared in
the PPTX run, while `link_href` is the raw URI from the PPTX
hyperlink.

## 2. Skipped rows

Rows with `wav_treatment="TBD"`, empty `wav_treatment` on a WAV-typed
row, or any unknown `wav_treatment` contribute no block to their
gram's DITA topic. They are recorded one-per-line in `skipped.txt`:

```
publication=main chapter=arctic-survey gram_id="Gram 05" topic_type=glc sequence=1 reason="wav_treatment is TBD"
```

The gram topic still renders provided at least one other row for the
same gram survived dispatch.

## 6. Ditamaps

### 6.1 Main ditamap (`main.ditamap`)

```xml
<map title="Main">
  <topichead navtitle="{Chapter Title}">
    <topicref href="main/{chapter-slug}/gram-NN/gram_NN.dita"/>
    <!-- ...one topicref per gram, in CSV order... -->
  </topichead>
  <!-- ...further chapters in alphabetical folder order... -->
</map>
```

Notes:

- The ditamap lives at the output root next to its sibling `main/`
  folder, so `topicref` URLs are simple forward paths into that
  folder (no `../` prefix).
- One `topicref` per gram — the CSV's N+1 rows per gram collapse into
  one `gram_NN.dita` and therefore one ditamap entry.
- `topichead` `navtitle` is the human-readable chapter title (mixed
  case), distinct from the chapter slug used in URLs.

### 6.2 Test ditamap (`progress-test-N.ditamap`)

```xml
<map title="Progress Test N">
  <topicref href="progress-test-N/gram-NN/gram_NN.dita"/>
  <!-- ...one topicref per gram, flat... -->
</map>
```

No `topichead` elements (FR-012, section 1.11 of the source spec).

## 7. Manifest (`manifest.txt`)

Plain text. One line per file produced. Sorted alphabetically.
Paths relative to `--out`. Includes ditamaps.

```
main.ditamap
main/arctic-survey/gram-01/analysis-sheet.docx
main/arctic-survey/gram-01/gram_01.dita
main/arctic-survey/gram-01/lofar-1.png
progress-test-1.ditamap
progress-test-1/gram-01/gram_01.dita
...
```

## 8. Filename conventions

| Artefact | Filename |
|---|---|
| Gram topic | `gram_NN.dita` (e.g. `gram_12.dita`) |
| Main ditamap | `main.ditamap` |
| Test ditamap | `progress-test-N.ditamap` (e.g. `progress-test-1.ditamap`) |

`NN` is the numeric portion of `gram_id` exactly as it appears in the
CSV (no padding adjustments). The expectation is that the source
material uses two-digit numbering today; if it grows past 99 the format
silently widens to three digits. There is exactly one DITA topic per
gram regardless of how many GLC/WAV links it carries — the legacy
per-link `gram_NN_lofarM.dita` filenames are obsolete.

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
│   │   │   ├── gram_NN.dita
│   │   │   ├── analysis-sheet.docx   ← analysis asset (or analysis.png)
│   │   │   ├── lofar-1.png           ← one image per GLC link (see §10)
│   │   │   ├── lofar-2.png
│   │   │   └── ...
│   │   └── gram-NN/
│   │       └── ...
│   └── {chapter-slug-2}/
│       └── ...
├── progress-test-1.ditamap
├── progress-test-1/
│   ├── gram-NN/
│   │   ├── gram_NN.dita
│   │   ├── analysis-sheet.docx
│   │   └── lofar-1.png
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

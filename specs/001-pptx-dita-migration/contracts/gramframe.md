# GramFrame integration contract

GramFrame is the browser-based spectrogram analysis tool that replaces
the legacy GAPS-Lite desktop application in the published DITA HTML.
The tool ships as a single self-contained JavaScript bundle
(`gramframe.bundle.js`) which auto-detects "gram-config" tables in
the rendered page on `DOMContentLoaded` and rewrites each one into an
interactive viewer.

Upstream integration guide:
<https://github.com/DeepBlueCLtd/GramFrame/blob/main/docs/HTML-Integration-Guide.md>

Everything below is the *contract* the DITA generator and HTML
publisher must satisfy so the bundle can recognise and replace each
table without further intervention.

## 1. Rendered HTML the bundle expects

```html
<table class="gram-config">
  <tr><td colspan="2"><img src="spectrogram.png" /></td></tr>
  <tr><td>time-start</td><td>0</td></tr>
  <tr><td>time-end</td><td>10</td></tr>
  <tr><td>freq-start</td><td>0</td></tr>
  <tr><td>freq-end</td><td>2000</td></tr>
</table>
```

Hard requirements:

- The root element is `<table>` with `class="gram-config"`. The bundle
  selects on this class; nested CSS classes added by DITA-OT (e.g.
  `class="table gram-config"`) are tolerated.
- Row 1 holds the spectrogram image inside a single `<td colspan="2">`.
  Without `colspan="2"` the bundle rejects the table.
- Rows 2–5 each carry exactly two cells: a parameter name in column 1
  and a numeric value in column 2. All four parameters
  (`time-start`, `time-end`, `freq-start`, `freq-end`) must be present.
  Values are parsed as floats. `time-end > time-start` and
  `freq-end > freq-start` are validated by the bundle.

Sequence in which the four parameter rows appear is not significant
(the bundle looks them up by name), but the generator emits them in
the order above for diff stability.

## 2. DITA source the generator emits

DITA-OT renders CALS tables into the HTML shape above. The generator's
DITA must therefore be:

```xml
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
      <row><entry>freq-start</entry><entry>{freq_start}</entry></row>
      <row><entry>freq-end</entry><entry>{freq_end}</entry></row>
    </tbody>
  </tgroup>
</table>
```

Notes:

- `outputclass="gram-config"` becomes a CSS class on the rendered
  `<table>` (DITA-OT also appends `class="table"`, which is harmless).
- The two named `<colspec>` elements are required. DITA-OT only emits
  `colspan="N"` on an `<entry namest=… nameend=…>` when the columns it
  spans are declared as colspecs by name. Without them the image cell
  renders with `colspan="1"` and GramFrame rejects the table.
- `time-start` is always `0`. `freq-start` and `freq-end` are **derived**
  from the GLC band settings (issue #87): `freq_start = bandcentre -
  bandwidth/2`, `freq_end = bandcentre + bandwidth/2`. The legacy assumption
  that `freq-start` is always `0` holds only when the band is centred at
  `bandwidth/2`; off-centre bands produce a non-zero (and possibly negative)
  `freq-start`. Limits are formatted deterministically: integer results carry
  no decimal point, non-integer results are trailing-zero-stripped. When
  `bandcentre` is blank the generator falls back to the legacy
  `freq-start=0`/`freq-end=bandwidth`; when `bandwidth` is also blank the
  limits are emitted blank rather than crashing.
- The image `href` is the bare local filename of the slugified asset
  copy that the generator places in the same per-gram folder as the
  topic (see `dita-topic-schema.md` §10).

## 3. Bundle loading in published HTML

The bundle is included via a `<script>` tag in every page that may
carry a GramFrame table. The tag is injected by `publish_html.py`
into the DITA-OT output (this concern is out of scope for the DITA
generator itself):

```html
<script src="gramframe.bundle.js"></script>
```

Either the standard bundle (`gramframe.js`) or the standalone bundle
(`gramframe.bundle.js`) works; the standalone form is preferred
because the published documentation is loaded from the local
filesystem (`file://`) on the air-gapped network, where the standard
bundle's module-loader path resolution can fail.

The bundle auto-initialises on `DOMContentLoaded` and scans the page
for `table.gram-config` instances. No further wiring is needed.

## 4. One table per `.glc` link

Each `.glc` link beneath a gram header in the source PPTX becomes
one `<table outputclass="gram-config">` inside the gram's single
DITA topic (`gram_NN.dita`). A gram with four `.glc` links therefore
produces four tables in the same topic, and the rendered page hosts
four GramFrame viewers stacked vertically — one per spectrogram.

## 5. `.glc` files whose inner asset is a `.wav`

All `Lofar` hyperlinks in the PPTX corpus target `.glc` files; none
target `.wav` directly. About 18% of the `.glc` files, however,
configure the on-PC GLC viewer to render a fresh spectrogram from a
sibling `.wav` rather than displaying a pre-rendered image. These
rows do not produce a GramFrame table — there is no static
spectrogram to embed. Instead the generator emits an `<xref>`
linking to the `.glc` and copies both the `.glc` and the named
`.wav` into the per-gram folder (see
[`dita-topic-schema.md`](./dita-topic-schema.md) §1.3). When a
student opens the link the on-PC GLC viewer loads the `.glc`, finds
the `.wav` next to it, and renders the spectrogram interactively.

The bundle ignores anything that is not a `table.gram-config`, so the
GLC-viewer-link blocks render as plain HTML next to the GramFrame
viewers without interference.

## 6. Persistent annotations: instructor vs student (GramFrame >= v0.1.10)

From v0.1.10 GramFrame persists each viewer's annotations (markers,
harmonics, the control-panel table) to browser storage and restores
them on reload. **Which storage it uses depends on a per-page context
it auto-detects.** On every save/load GramFrame calls
`document.getElementById("gf-persistent")`:

- **Trainer (instructor) context** — when an element with
  `id="gf-persistent"` is present (or, as a fallback heuristic, an
  `<a>` whose trimmed text is exactly `ANALYSIS`). Annotations are
  written to `localStorage`, so they **survive across reloads and
  browser sessions**.
- **Student context** — when neither is present. Annotations go to
  `sessionStorage` and are **cleared when the tab closes**.

Storage keys are namespaced per page path (`gramframe::<pathname>`,
suffixed `::<n>` for the n-th viewer on a multi-gram page), so grams on
different pages never collide.

The generator satisfies this contract by rendering the marker id as the
HTML `id` of the **instructor-only edition marker** it already stamps on
every topic body (`GF_PERSISTENT_MARKER_ID` in `generate_dita.py`):

```xml
<p audience="-trainee" id="gf-persistent" outputclass="edition-instructor"/>
```

Because the marker carries `audience="-trainee"`, the trainee DITAVAL
strips it from the student build. The instructor edition therefore ships
`id="gf-persistent"` (→ `localStorage`, annotations persist) while the
student editions ship neither the id nor an `ANALYSIS` link (→
`sessionStorage`, annotations are ephemeral). No new element and no new
profiling axis are introduced — the persistence opt-in rides the exact
same instructor-only DITAVAL filtering as the edition stylesheet signal.
DITA-OT and Oxygen both pass an explicit `@id` straight through to the
rendered HTML `id` (the in-page analysis-sheet jump link relies on the
same passthrough), so `getElementById` finds it.

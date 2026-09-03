# Gram navigation bar for the Oxygen WebHelp Responsive template

A drop-in overlay that puts the **per-gram jump links into the WebHelp
toolbar** — the strip that already carries the maximise, collapse and print
buttons — so they are always on screen and cost the gramframe no width. Like
`../oxygen-hide-search/`, it is **not** a complete theme: it is one stylesheet,
one small script and a `<body>` fragment you add to your own Oxygen WebHelp
Responsive template (the Fi3ldMan-derived one that already hosts the GramFrame
overlay).

> Formerly `theme/gram-nav-panel/`, which pinned the same links as a floating
> panel in the lower-right corner. Issue #179 moved them into the toolbar.

## What it does

`generate_dita.py` emits one `<p outputclass="gram-nav">` on every gram page
(`_append_gram_nav_panel`). Oxygen passes `outputclass` through to the HTML
`@class`, so the published page carries `<p class="gram-nav">` holding one
in-page link per content section, **in page order**. Which entries survive is
decided at **build time** by the DITAVAL profiles, not by this overlay:

| entry | `audience` | edition |
| --- | --- | --- |
| `7 Questions` | `student-only` | student |
| `Lofar N`, `WAV N`, `Demon N` | *(none)* | both |
| `Analysis Sheet` | `-trainee` | instructor |

The Lofar and WAV numbers are independent 1..N sequences, so a gram whose deck
interleaved them reads `Lofar 1`, `WAV 1`, `Lofar 2`. Because the filtering has
already happened, **one** stylesheet and **one** script serve both scenarios.

- `resources/gram-nav.js` moves the paragraph into `<nav class="wh_tools">`,
  immediately before the `.wh_right_tools` button cluster, and stamps
  `wh_tools_gram_nav` on the toolbar and `wh_tools_row_gram_nav` on its row.
- `resources/gram-nav.css` styles it as a horizontal, wrapping strip of link
  chips and sticks the toolbar row to the top of the viewport, so the links
  stay reachable the whole way down a long gram page.

On pages with no `gram-nav` paragraph (welcome, security, week and publication
indexes) the script returns early, no marker class is applied, and every rule
in the stylesheet matches nothing — those toolbars keep the stock behaviour,
non-sticky included.

## The problem it fixes (issue #179)

The gram page is a wide spectrogram driven by GramFrame; page width is the most
valuable thing on it. Two things were spending that width:

1. Oxygen's per-topic **"On this page" mini-TOC** (`<nav id="wh_topic_toc">`)
   reserved a full-height column down the right edge for its two-to-six links.
   Collapsing it recovered the space but lost the links.
2. This overlay's own predecessor floated the same links as a fixed panel over
   the lower-right corner of the gram.

The mini-TOC turned out to be a **derived, audience-blind duplicate** of the
`gram-nav` paragraph — across the corpus the two carry the same anchors, page
for page and edition for edition — so it is retired outright rather than
relocated. The template now publishes with **`webhelp.show.topic.toc=no`**,
which is what frees the width: Oxygen's own `topicComponentsExpander.xsl` (mode
`fix-content-width`) hands `#wh_topic_body` the full `col-12` when neither the
publication TOC nor the topic TOC is generated, and this template already
publishes with `webhelp.show.publication.toc=no`. No CSS width override, no
fight with the mini-TOC's own sizing script.

That leaves `gram-nav` as the single list — the better of the two, because the
pipeline authors it, the DITAVAL filters it per edition, and it exists even on
grams too small for Oxygen to generate a mini-TOC at all (its guard is
`count(li) > 1`). This overlay puts it where the reader can always see it.

## Layout

```text
gram-nav-bar/
├── page-templates-fragments/
│   └── libraries/
│       └── gram-nav.xml    ← loads gram-nav.js at the end of <body> on topic pages
└── resources/
    ├── gram-nav.css        ← styles the links as a bar in the toolbar; sticks the toolbar
    └── gram-nav.js         ← moves <p class="gram-nav"> into <nav class="wh_tools">
```

The folder names mirror the Fi3ldMan template's own, so the files drop straight
in.

## Why a script rather than pure CSS

The paragraph and the toolbar sit in different subtrees of the page — the
toolbar is in `#wh_topic_container`'s first row, the paragraph inside
`.wh_content_area` — and CSS cannot reparent an element. Absolutely positioning
the paragraph over the toolbar instead would have to guess the bar's height and
margins, and would collide with the button cluster the moment the links wrapped.
Ten lines of DOM move is the honest version, and it gives the stylesheet the
marker classes that keep every rule off the non-gram pages.

## Wiring it into the (single, shared) template

> **Already wired in `../pptx-transform/`**, this repo's own publishing
> template — verbatim copies of all three payload files, the `<css>` and
> `<fragment>` entries, and the `webhelp.show.topic.toc` parameter. Run
> `../sync.py` after editing a payload here. The steps below are for
> installing into a **different** template.

1. **Use your existing publishing template** (the Fi3ldMan-derived one that
   hosts the GramFrame overlay — see `../gramframe-oxygen/README.md`).

2. **Copy `resources/gram-nav.css` and `resources/gram-nav.js`** into that
   template's `resources/` directory, and
   `page-templates-fragments/libraries/gram-nav.xml` into its
   `page-templates-fragments/libraries/`.

3. **Turn the mini-TOC off.** In the template's `.opt`, inside `<parameters>`:

   ```xml
   <parameter name="webhelp.show.topic.toc" value="no"/>
   ```

4. **Reference the stylesheet** from `<resources>` so it loads after the stock
   styles and wins the cascade:

   ```xml
   <resources>
     <!-- …existing entries (GramFrame bundle, hide-search.css, …)… -->
     <css file="resources/gram-nav.css"/>
   </resources>
   ```

5. **Bind the fragment** inside `<html-fragments>`:

   ```xml
   <fragment file="page-templates-fragments/libraries/gram-nav.xml"
             placeholder="webhelp.fragment.after.body.topic.page"/>
   ```

   Oxygen binds **one fragment per placeholder**; `after.body.topic.page` is
   deliberate, and the remaining free ones are few. See `gram-nav.xml`'s own
   comment for which placeholders this template has already spent.

6. **Point both scenarios at this template.** The instructor *and* the student
   WebHelp Responsive transformation scenarios share this one template; the
   DITAVAL filter decides per page which entries survive.

7. **Republish both editions and confirm:** on a gram page the jump links sit
   as a horizontal strip in the toolbar, the toolbar stays put as you scroll,
   the gramframe spans the full page width with no right-hand column, and there
   is no "On this page" panel; on an instructor page the strip ends with the
   amber **Analysis Sheet** entry and on the matching student page it does not;
   clicking an entry scrolls to that stage; and a non-gram page
   (welcome/index/week) is unchanged, with a non-sticky stock toolbar.

## Oxygen-only, like every overlay here

The production Oxygen publish is the only renderer this targets. `.wh_tools`
is WebHelp Responsive chrome that exists nowhere else — `publish_html.py`'s
DITA-OT HTML5 preview emits no toolbar, and carries no stylesheet at all — so
there is no second rendering to keep in step. Tune it against the committed
Oxygen build; `../sync.py` copies a CSS or JS edit straight into
`demo/oxygen-sample/published/` for a hard refresh, no republish.

**A republish *is* needed for this overlay's other two halves**, though: the
`webhelp.show.topic.toc` parameter and the fragment binding are read at publish
time, not deployed as files.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (alongside
the other overlays), so it lands
at `ROOT\theme\gram-nav-bar\` on the target. The operator installs it into the
Oxygen template once, per step 2 above. See README.md, *"Getting pipeline
updates onto the target"*.

## Sources

- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>
- HTML fragment placeholders in the WebHelp Responsive page templates:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/whr-html-fragments.html>

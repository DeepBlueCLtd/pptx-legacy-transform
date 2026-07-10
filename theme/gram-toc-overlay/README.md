# Floating "On this page" mini-TOC overlay for the Oxygen WebHelp template

A drop-in CSS overlay that **floats the WebHelp per-topic "On this page"
mini-TOC as a compact top-right overlay on gram pages**, so it stops reserving
a full-height right-hand column and lets the gramframe use the full page width.
Like `../oxygen-hide-search/` and `../gram-nav-panel/`, it is **not** a complete
theme — it is one CSS file (plus the wiring) you add to your own Oxygen WebHelp
Responsive template (the Fi3ldMan-derived one that already hosts the GramFrame
overlay).

## The problem it fixes

Oxygen WebHelp Responsive renders the per-topic **"On this page"** table of
contents as `<nav id="wh_topic_toc">`, a **flex sibling** of the content column
(`<div id="wh_topic_body">`) inside the topic's `<div class="row">`:

```html
<div class="row">
  <div id="wh_topic_body" class="… col-lg-12 col-md-9"> … gramframe … </div>
  <nav id="wh_topic_toc" class="d-none d-lg-block navbar"> … On this page … </nav>
</div>
```

As an in-flow flex item, `#wh_topic_toc` reserves a **full-height strip down the
right edge for the entire scroll length of the page** — even though its own
content is just a couple of links (`7 Questions`, `Lofar 1`). The gramframe
lives in `#wh_topic_body` and sizes itself to that column, so the reserved strip
squeezes it narrower (and, because the gramframe keeps its aspect ratio,
shorter). Collapsing the mini-TOC with its own toggle button visibly lets the
gramframe grow — this overlay makes that the default while **keeping the TOC
visible**.

## What it does

1. Gives the content column the **full row width** (overrides the `col-md-9` /
   `col-lg-*` Bootstrap width), so the gramframe spans the whole page.
2. **Lifts `#wh_topic_toc` out of the flex flow** and pins it as a compact
   overlay in the **top-right** of the content area, only as tall as its own
   links — so it no longer steals a full-height column. It sits above the
   gramframe (which is lower down the page, under the Lofar heading), not over
   it, and scrolls up out of the way as the reader moves to the gramframe.
   Oxygen's own collapse/expand toggle keeps working.

## Layout

```text
gram-toc-overlay/
└── resources/
    └── gram-toc-overlay.css   ← floats #wh_topic_toc as a top-right overlay on gram pages
```

The folder name mirrors the Fi3ldMan template's `resources/` so the file drops
straight in.

## How it tells gram pages apart (no template divergence)

It scopes to gram pages with `body:has(p.gram-nav)`. Every gram page carries
`<p class="gram-nav">` — the unfiltered in-page Lofar jump links — in **both**
editions (see `../gram-nav-panel/`). Non-gram pages (welcome, security, week /
publication indexes) carry none, so the overlay matches gram pages exactly and
leaves every other page's mini-TOC untouched. `:has()` is the same selector
mechanism `../oxygen-hide-search/` already relies on.

## Oxygen-only — no dev-preview counterpart

Unlike `../gram-nav-panel/`, this overlay has **no** dev/CI HTML-preview
counterpart to keep in step. The "On this page" mini-TOC is an Oxygen WebHelp
Responsive feature; `publish_html.py`'s DITA-OT HTML5 preview never emits
`#wh_topic_toc`, so there is nothing to mirror in
`scripts/vendor/themes/operator-console-v2/theme.css`.

## Wiring it into the (single, shared) template

Identical to `../gram-nav-panel/`:

1. **Use your existing publishing template** (the Fi3ldMan-derived one that
   hosts the GramFrame overlay — see `../gramframe-oxygen/README.md`).

2. **Copy `resources/gram-toc-overlay.css`** into that template's `resources/`
   directory.

3. **Reference it from the template descriptor.** Open the template's `.opt`
   file and add the CSS inside `<resources>` so it loads after the stock styles
   and wins the cascade:

   ```xml
   <resources>
     <!-- …existing entries (GramFrame bundle, hide-search.css, gram-nav.css, …)… -->
     <css file="resources/gram-toc-overlay.css"/>
   </resources>
   ```

4. **Point both scenarios at this template.** The instructor *and* the student
   WebHelp Responsive transformation scenarios share this one template; the
   overlay behaves the same in both.

5. **Republish both editions and confirm:** on a gram page the gramframe now
   spans the full page width, and the "On this page" mini-TOC floats as a
   compact box in the top-right instead of reserving a full-height right-hand
   column; its collapse/expand toggle still works; and a non-gram page
   (welcome / index) is unchanged.

## Tuning (per target, in the CSS)

- **Panel position** — the `top` / `right` on the `#wh_topic_toc` rule.
- **Panel width cap** — the `max-width` on the same rule.
- **Follow the scroll** — if you'd rather the panel stay pinned in the viewport
  as the reader scrolls (instead of sitting at the top of the topic), swap
  `position: absolute` for `position: fixed` and drop the `.wh_content_area`
  rule. Note a fixed panel will then float **over** the full-width gramframe as
  you scroll past it.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (alongside
`gramframe-oxygen/`, `oxygen-hide-search/` and `gram-nav-panel/`), so it lands
at `ROOT\theme\gram-toc-overlay\` on the target. The operator installs it into
the Oxygen template once, per step 2 above. See README.md, *"Getting pipeline
updates onto the target"*.

## Sources

- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>

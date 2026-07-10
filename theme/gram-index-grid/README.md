# Gram index grid for the Oxygen WebHelp Responsive template

A drop-in CSS overlay that lays out the **gram index** on every week / chapter
landing page and progress test as a **re-flowing grid of rounded tiles** in the
**production Oxygen publish**, exactly as
`scripts/vendor/themes/operator-console-v2/theme.css` does for the dev/CI HTML
preview. Like `../gram-nav-panel/` and `../oxygen-hide-search/`, it is **not** a
complete theme — it is one CSS file (plus the wiring) you add to your own Oxygen
WebHelp Responsive template (the Fi3ldMan-derived one that already hosts the
GramFrame overlay).

## What it does

`generate_dita.py` emits each week / chapter landing page (and each progress
test) with a `<ul outputclass="gram-index">` whose items are
`<xref outputclass="enterBtn">` links, one per gram
(`emit_main_chapter_topics` and the progress-test grams topic). Oxygen passes
`outputclass` through to the HTML `@class`, so the published page carries:

```html
<ul class="… ul gram-index">
  <li class="… li"><a class="… xref enterBtn" href="…">Gram 01</a></li>
  …
</ul>
```

Untouched, the stock WebHelp stylesheet renders that as a tall single-column
bullet list — one gram per line, `Gram 01 … Gram 31` down the left edge with
the rest of the page empty. `gram-index-grid.css` restyles the same `<ul>` as a
CSS grid of equal rounded rectangles that wrap to the width of the content
column, so a 30-gram week reads as a compact, scannable board. Each tile is the
whole link, so the entire rectangle is the click target. On pages with no
`gram-index` list (welcome, security, individual gram pages) the rule simply
matches nothing.

## Layout

```text
gram-index-grid/
└── resources/
    └── gram-index-grid.css   ← lays out <ul class="gram-index"> as a tile grid
```

The folder name mirrors the Fi3ldMan template's `resources/` so the file drops
straight in.

## Wiring it into the (single, shared) template

Identical to `../gram-nav-panel/`:

1. **Use your existing publishing template** (the Fi3ldMan-derived one that
   hosts the GramFrame overlay — see `../gramframe-oxygen/README.md`).

2. **Copy `resources/gram-index-grid.css`** into that template's `resources/`
   directory.

3. **Reference it from the template descriptor.** Open the template's `.opt`
   file and add the CSS inside `<resources>` so it loads after the stock styles
   and wins the cascade:

   ```xml
   <resources>
     <!-- …existing entries (GramFrame bundle, hide-search.css, gram-nav.css, …)… -->
     <css file="resources/gram-index-grid.css"/>
   </resources>
   ```

4. **Point both scenarios at this template.** The layout is edition-agnostic —
   the instructor *and* student WebHelp Responsive transformation scenarios
   share this one template and stylesheet.

5. **Republish and confirm:** open a week landing page (e.g. `Week 1`) and check
   the grams render as a grid of rounded tiles that reflow when you narrow the
   window; hovering a tile lifts it with the accent border; and a page with no
   gram list (welcome/index/individual gram) is unaffected.

## Keep it in step with the dev preview

The grid layout here mirrors the `ul.gram-index` rule in
`scripts/vendor/themes/operator-console-v2/theme.css` so the Oxygen production
output and the `publish_html.py` dev preview lay the index out the same way.
The dev-preview rule uses the theme's dark CSS custom properties; this file uses
literal colours tuned to the light stock WebHelp template (accent `#0d6cfd`, the
template's own link colour) because the Oxygen WebHelp output does not load that
theme. When you restyle one, restyle the other.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (alongside
`gramframe-oxygen/`, `gram-nav-panel/`, and `oxygen-hide-search/`), so it lands
at `ROOT\theme\gram-index-grid\` on the target. The operator installs it into
the Oxygen template once, per step 2 above. See README.md, *"Getting pipeline
updates onto the target"*.

## Sources

- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>

# Floating gram navigation panel for the Oxygen WebHelp Responsive template

A drop-in CSS overlay that styles the **floating gram navigation panel** in
the **production Oxygen publish**, exactly as
`scripts/vendor/themes/operator-console-v2/theme.css` already does for the
dev/CI HTML preview. Like `../oxygen-hide-search/`, it is **not** a complete
theme — it is one CSS file (plus the wiring) you add to your own Oxygen
WebHelp Responsive template (the Fi3ldMan-derived one that already hosts the
GramFrame overlay).

## What it does

`generate_dita.py` emits one `<p outputclass="gram-nav">` on every gram page.
Oxygen passes `outputclass` through to the HTML `@class`, so the published
page carries `<p class="gram-nav">` holding:

- one in-page link per **Lofar** (`href="#…/lofar-N"`, label `Lofar N`) — these
  are unfiltered, so they appear in **both** editions; and
- **instructor edition only**, a final link to the **Analysis Sheet**. Its
  `<xref>` carries `audience="-trainee"`, so the trainee DITAVAL filter strips
  that one entry from the student build (its target section is instructor-only
  too, so the student edition never ships a dangling anchor).

`gram-nav.css` pins that paragraph as a fixed panel in the lower-right corner
so a reader — student or instructor — can jump straight to a numbered Lofar
from anywhere on a long gram page. On pages with no `gram-nav` paragraph
(welcome, security, week and publication indexes) the rule simply matches
nothing.

> Earlier the panel was the **instructor-only** "Analysis Sheet" pill
> (issue #91). It now serves students and instructors alike: students get the
> Lofar links, instructors additionally get the Analysis Sheet link.

## Layout

```text
gram-nav-panel/
└── resources/
    └── gram-nav.css   ← pins <p class="gram-nav"> as a fixed lower-right panel
```

The folder name mirrors the Fi3ldMan template's `resources/` so the file drops
straight in.

## How it tells the editions apart (no template divergence)

It doesn't need to — the **pipeline** does. The Lofar links are unfiltered and
the Analysis Sheet link carries `audience="-trainee"`, so the trainee DITAVAL
profile (the one the student transformation scenario already passes via
`args.filter`) removes the instructor entry before this CSS ever runs. Both
editions share **one** stylesheet and **one** publishing template, the same
arrangement `../oxygen-hide-search/README.md` describes.

## Wiring it into the (single, shared) template

Identical to `../oxygen-hide-search/`:

1. **Use your existing publishing template** (the Fi3ldMan-derived one that
   hosts the GramFrame overlay — see `../gramframe-oxygen/README.md`).

2. **Copy `resources/gram-nav.css`** into that template's `resources/`
   directory.

3. **Reference it from the template descriptor.** Open the template's `.opt`
   file and add the CSS inside `<resources>` so it loads after the stock
   styles and wins the cascade:

   ```xml
   <resources>
     <!-- …existing entries (GramFrame bundle, hide-search.css, …)… -->
     <css file="resources/gram-nav.css"/>
   </resources>
   ```

4. **Point both scenarios at this template.** The instructor *and* the
   student WebHelp Responsive transformation scenarios share this one
   template; the DITAVAL filter decides per page whether the Analysis Sheet
   entry survives.

5. **Republish both editions and confirm:** on an instructor gram page the
   panel lists `Lofar 1 … Lofar N` and a final amber **Analysis Sheet** entry;
   on the matching student page it lists the Lofars only, with no Analysis
   Sheet entry; clicking an entry scrolls to that Lofar (or the Analysis
   Sheet); and a non-gram page (welcome/index) shows no panel.

## Keep it in step with the dev preview

The colours and layout here mirror the `article p.gram-nav` rule in
`scripts/vendor/themes/operator-console-v2/theme.css` so the Oxygen production
output and the `publish_html.py` dev preview render the panel the same way.
The dev-preview rule uses the theme's CSS custom properties; this file uses
literal colours because the Oxygen WebHelp output does not load that theme.
When you restyle one, restyle the other.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (alongside
`gramframe-oxygen/` and `oxygen-hide-search/`), so it lands at
`ROOT\theme\gram-nav-panel\` on the target. The operator installs it into the
Oxygen template once, per step 2 above. See README.md, *"Getting pipeline
updates onto the target"*.

## Sources

- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>

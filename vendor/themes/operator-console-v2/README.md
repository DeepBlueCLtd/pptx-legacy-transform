Operator Console v2 — dark theme for the published DITA HTML.

Source: mockups/index-dark/theme.css (a strict superset of the gram-topic
theme at mockups/theme-console-v2/theme.css — same first 351 lines plus
~170 lines of index-page rules). Vendored as a single stylesheet so every
published HTML page (gram topic, DITA-OT map index, hand-written landing,
…) can link the same file.

## How the theme classifies a page

The theme works on raw DITA-OT HTML5 output — no post-publish injector
required, no DITA-OT plugin, no JavaScript. Every variation is driven by
CSS `:has()` selectors that key off elements DITA-OT already emits:

| Variation         | CSS selector                       | Why it matches              |
|-------------------|------------------------------------|-----------------------------|
| Ditamap index     | `body:has(ul.map)`                 | `ul.map` only exists on the per-ditamap index page DITA-OT emits |
| Instructor edition | `body:has(.ph)`                   | Every `<ph>` in the DITA source is `audience="-trainee"` (chapter prefix, map-title suffix, vessel-name); the student DITAVAL strips them all |
| Student edition   | `body:not(:has(.ph))`              | Inverse of the instructor detector |

Compound selectors used in the file:

- `body:has(ul.map):has(.ph)`           — instructor index page
- `body:has(ul.map):not(:has(.ph))`     — student index page

This means the theme produces the right look on either edition with zero
host involvement beyond linking the stylesheet.

## What the host must still do

The theme stops at styling. The host (Oxygen XML Author publishing via
a template, or `publish_html.py` on the dev side) is responsible for:

1. Copying `theme.css` into the published output tree.
2. Adding a `<link rel="stylesheet" href="…/theme.css">` to every page.
3. Vendoring `gramframe.bundle.js` and a `<script src="…">` reference
   on every page (so the spectrogram tables become interactive).
4. Running DITA-OT with the trainee DITAVAL filter for the student
   edition and without it for the instructor edition.

`publish_html.py` does all four for the dev/CI pipeline. The air-gapped
Oxygen publish does (1)–(3) via the publish template (the same pattern as
the pub-9 / pub-10 work) and (4) via Oxygen's built-in DITAVAL UI.

## Browser support

`:has()` is Baseline 2023 — supported in current Chromium, Firefox,
and Safari. If the target ships an older browser, the theme degrades
gracefully: the instructor banner appears on every page and the
per-edition tile-density overrides don't fire, but content remains
readable.

## Hooks the theme uses

DITA `outputclass` values that the theme styles (DITA-OT copies these
through to HTML `class`):

- `lofar-stage`     — the faux instrument trace look for each LOFAR section
- `analysis-sheet`  — the analyst's worksheet section (instructor only)
- `gram-config`     — table picked up by the GramFrame plugin
- `vessel-name`     — the amber target-name pill on a gram heading

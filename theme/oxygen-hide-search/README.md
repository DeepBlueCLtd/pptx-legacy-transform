# Hide the search bar in the student Oxygen edition (issues #93, #178)

The **student** edition of the published documentation has no searchable
content: the trainee DITAVAL filter strips the instructor-only text
(Analysis Sheets, vessel names), leaving grams that are images with no
body text, so the WebHelp search box only ever returns "no results". This
overlay hides that search box **in the student edition only**.

The instructor edition keeps its search box on **every** page — it *does*
carry searchable text, so search stays useful there.

## How it tells the editions apart

The two editions publish as **two transformation scenarios**, so which edition
is being built is known at **build time**. One parameter says so:

| Scenario | `webhelp.show.search` | Result |
| --- | --- | --- |
| instructor | *(template default)* `yes` | box shown on every page |
| student | `no` | box hidden on every page |

`customSearchFlag.xsl` turns that parameter into a hidden `.wh-search-hidden`
marker, injected on every page via the `webhelp.fragment.after.header`
placeholder; `hide-search.css` hides `#searchForm` wherever the marker appears.

Only the exact value `no` hides the box. A misspelled or unset parameter leaves
the stock behaviour — a student edition with a useless search box is a wart, an
instructor edition without one is a defect.

There is still **one shared template**: the two scenarios differ only in their
`args.filter` DITAVAL and this one parameter. No student-variant template to
keep in step.

## What changed in #178, and why

This overlay used to infer the edition from the **page content**:

```css
body:not(:has(.gf-persistent)) #searchForm { display: none !important; }
```

`generate_dita.py` stamps a hidden, instructor-only `<p class="gf-persistent">`
(carrying `audience="-trainee"`) onto every **topic**; the trainee DITAVAL
strips it, so marker-present meant instructor and marker-absent meant student.

**That inference only holds on pages built from a topic.** Oxygen builds
`index.html` from the *ditamap* and generates `search.html` outright, so
neither carries the marker in *either* edition. Measured on the instructor
edition:

| Page | Built from | Marker | Box shown? |
| --- | --- | --- | --- |
| `week-1/week_1.html` | topic | 1 | yes |
| `welcome.html` | topic | 1 | yes |
| `security.html` | topic | 1 | yes |
| `index.html` | **ditamap** | **0** | **no** ← the bug |
| `search.html` | **generated** | **0** | **no** |

With `webhelp.show.main.page.tiles=yes`, `index.html` is where an instructor
*arrives*. The edition that is supposed to keep search lost the box at exactly
the point a reader would reach for it.

Two other directions were considered and rejected:

- **Exempt the generated pages** (scope the rule to `body.wh_topic_page`).
  Cheapest, but it hands the *student* edition a visible-but-useless box on
  `index.html` — the one page a student is guaranteed to see.
- **Invert the test against a student-side marker.** There is none: the DITAVAL
  scheme strips elements, it does not add them.

The scenario parameter is exact on every page in both editions. It became cheap
once issue #175 brought XSLT extensions into the template for the protective
marking; the two share that plumbing.

### `search.html` is now deliberate

The instructor edition keeps its search box on the search-results page. The
student edition hides it there too. Both are intended, and neither is the
"negligible wart" this README used to describe — that caveat is gone because the
behaviour it described is gone.

## What's here

```text
oxygen-hide-search/
├── page-templates-fragments/
│   └── search-flag.xml        ← empty <div class="wh_search_visibility"/>
├── resources/
│   └── hide-search.css        ← hides #searchForm where the marker appears
└── xslt/inc/
    └── customSearchFlag.xsl   ← parameter → marker (or nothing)
```

`#searchForm` is the stable id Oxygen WebHelp Responsive assigns the search
input widget on every generated page (welcome/index, topic, and the
search-results page), so one rule covers all of them.

`hide-search.css` also keeps `.gf-persistent { display: none }`. That marker no
longer drives anything here, but `generate_dita.py` still stamps it and the
empty paragraph must never show.

## Why not a stock parameter

Oxygen WebHelp Responsive has **no built-in parameter that disables search**
(confirmed against the WebHelp Responsive parameter list and the Oxygen forum),
which is why this overlay defines its own and applies it with a small CSS rule
rather than editing stock templates.

## Already done for you in `theme/pptx-transform/`

If you publish with this repo's own template, this is **already wired in**.
Point *both* scenarios' **Templates** tab at `pptx-transform.opt`, then set
`webhelp.show.search` = `no` on the **student** scenario only. Leave the
instructor scenario alone.

## Wiring it into a different template

1. Copy `resources/hide-search.css`,
   `page-templates-fragments/search-flag.xml` and
   `xslt/inc/customSearchFlag.xsl` into that template.
2. Declare `<parameter name="webhelp.show.search" value="yes"/>` in its `.opt`.
3. Add `<css file="resources/hide-search.css"/>` after the stock stylesheets so
   it wins the cascade.
4. Bind the fragment:

   ```xml
   <fragment file="page-templates-fragments/search-flag.xml"
             placeholder="webhelp.fragment.after.header"/>
   ```

5. Import `inc/customSearchFlag.xsl` from a stylesheet bound to **each** of the
   four page-type XSLT extension points (see
   `../oxygen-protection/README.md`, which lists them). Miss the main-page one
   and `index.html` regresses to exactly the #178 bug.
6. Set `webhelp.show.search` = `no` on the student scenario, and republish both
   editions to confirm.

> Dropping the CSS into `webhelp.custom.resources` instead will **not** work:
> that parameter only *copies* the file to the output, it does not link it into
> the page `<head>`, and loading the CSS is what hides the box.

## Dev/CI preview note

This overlay is for the **production Oxygen publish**. The
`scripts/publish_html.py` DITA-OT dev preview does not emit a WebHelp search
box at all, so there is nothing to hide there; its theme simply hides the
`.gf-persistent` marker so the empty paragraph never shows.

## Sources

- Removing the search bar (Oxygen forum, CSS approach):
  <https://www.oxygenxml.com/forum/topic13228.html>
- WebHelp Responsive transformation parameters (no disable-search param):
  <https://www.oxygenxml.com/doc/ug-webhelp-responsive/topics/webhelp-responsive-plugin-additional-parameters.html>
- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>

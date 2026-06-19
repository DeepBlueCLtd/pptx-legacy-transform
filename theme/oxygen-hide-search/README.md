# Hide the search bar in the student Oxygen edition (issue #93)

The **student** edition of the published documentation has no searchable
content: the trainee DITAVAL filter strips the instructor-only text
(Analysis Sheets, vessel names), leaving grams that are images with no
body text, so the WebHelp search box only ever returns "no results". This
overlay hides that search box **in the student edition only**, entirely
through the Oxygen **transformation scenario** — no custom XSL and no
change to the pipeline source (`scripts/`, `dita/`, the ditamaps).

The instructor edition keeps its search box: it *does* carry searchable
text, so search stays useful there.

## What's here

```text
oxygen-hide-search/
└── resources/
    └── hide-search.css   ← one rule: #searchForm { display: none }
```

`#searchForm` is the stable id Oxygen WebHelp Responsive assigns the search
input widget on every generated page (welcome/index, topic, and the
search-results page), so one rule covers all of them. This is exactly the
approach the Oxygen team recommend on their forum for removing the search
bar — CSS, not template surgery — see *Sources* below.

## Why CSS, not a transformation parameter

Oxygen WebHelp Responsive has **no built-in parameter that disables search**
(confirmed against the WebHelp Responsive parameter list and the Oxygen
forum). The supported, scenario-level way to suppress it without editing
stock templates or writing XSL is to add a small custom CSS that the output
loads last (so it overrides the stock styles) — and the supported way to
load a custom CSS from a transformation scenario is an Oxygen **Publishing
Template** with a `<css>` resource entry.

## Wiring it into the student scenario

You already run a **separate transformation scenario per edition** (the
instructor scenario and the trainee-filtered student scenario — the one
that passes `args.filter` / the `trainee.ditaval` profile). Add the CSS to
the **student scenario only**.

The project already publishes through a custom WebHelp Responsive publishing
template (the Fi3ldMan-derived one that hosts the GramFrame overlay — see
`../gramframe-oxygen/README.md`). The cleanest setup is a **student variant**
of that publishing template that adds this one CSS file on top:

1. **Duplicate your existing publishing template folder** (the one with the
   GramFrame bundle wired in) to a student variant, e.g.
   `…/templates/student/`. Keep everything the instructor template has — the
   student edition still renders grams, so it still needs the GramFrame
   bundle and its `<head>` script.

2. **Copy `resources/hide-search.css`** from this folder into the student
   template's `resources/` directory.

3. **Reference it from the template descriptor.** Open the student template's
   `.opt` file and add the CSS inside `<resources>` so it loads after the
   stock styles and wins the cascade:

   ```xml
   <resources>
     <!-- …existing entries (GramFrame bundle, theme.css, …)… -->
     <css file="resources/hide-search.css"/>
   </resources>
   ```

4. **Point the student scenario at the student template.** Edit the
   **student** WebHelp Responsive transformation scenario → **Templates**
   tab → select the new student publishing template. (Duplicate the stock
   scenario first if you haven't — the built-ins are read-only.) Leave the
   **instructor** scenario on the original template so its search box stays.

5. **Republish the student edition and confirm** the search box is gone from
   the welcome page, a topic page, and that the rest of the header/layout is
   unchanged. The instructor edition still shows its search box.

> If you would rather not maintain two publishing templates, you can instead
> keep one template and drop `hide-search.css` into the folder you pass to
> the `webhelp.custom.resources` parameter — but `webhelp.custom.resources`
> only *copies* the file to the output, it does **not** link it into the
> page `<head>`. Loading the CSS is what hides the box, so the Publishing
> Template route above (which links it) is the reliable one.

## Dev/CI preview note

This overlay is for the **production Oxygen publish**. The
`scripts/publish_html.py` DITA-OT dev preview is inspection-only and is not
the delivered output, so it is intentionally left untouched here.

## Sources

- Removing the search bar (Oxygen forum, CSS approach):
  <https://www.oxygenxml.com/forum/topic13228.html>
- WebHelp Responsive transformation parameters (no disable-search param):
  <https://www.oxygenxml.com/doc/ug-webhelp-responsive/topics/webhelp-responsive-plugin-additional-parameters.html>
- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>

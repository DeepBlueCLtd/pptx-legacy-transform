# Publish dark, with no theme picker (issue #173)

The Oxygen WebHelp Responsive template offers the reader a **light / dark
theme menu** (Auto · Light · Dark) and defaults to whatever their browser
prefers. The AAAC publications are read as **dark** — the dev/CI preview
already publishes the dark Operator Console theme
(`scripts/vendor/themes/operator-console-v2/`), and a spectrogram reads
better on a dark page — so the production Oxygen publish should ship dark
and offer no choice.

This overlay does both. Like `../oxygen-hide-search/`, `../gram-nav-panel/`
and `../gram-toc-overlay/`, it is **not** a complete theme — it is two small
files (plus the wiring) you add to your own Oxygen WebHelp Responsive
template (the Fi3ldMan-derived one that already hosts the GramFrame overlay).

## How it works

Oxygen marks a dark page by setting **`data-wh-theme="dark"` on the `<html>`
element**; the template's own stylesheet swaps its CSS custom properties under
`:root[data-wh-theme="dark"]`. Light is simply the **absence** of that
attribute.

The stock `themes.js` sets the attribute at load time from the reader's stored
choice (localStorage) or their `prefers-color-scheme`. Crucially it only ever
**sets** the attribute — nothing but a click in the theme menu removes it. So:

1. **`resources/dark-mode.js`** pins `data-wh-theme="dark"` on `<html>`. It is
   loaded from a `<head>` fragment **without `defer`**, so it runs before the
   first paint (a deferred version would flash light for a frame). Whatever
   `themes.js` decided, and whatever the reader picked on an earlier visit,
   the page renders dark.
2. **`resources/dark-mode.css`** hides `.wh_theme` — the header wrapper holding
   the `#wh_theme_button` toggle and the Auto/Light/Dark dropdown that
   `topic.js` builds inside it — so the published output carries no control
   that could unpin the theme.

Both editions share this, exactly like the sibling overlays: nothing here is
audience-aware, so instructor and student pages are dark alike.

The two files were checked against a real WebHelp Responsive 28.1 page (the
Oxygen user guide's own output) driven headlessly: with the overlay in the
`<head>`, the page came up dark and the picker hidden for every combination of
browser `prefers-color-scheme` (light/dark) and previously stored choice
(none/light/dark); without it, the same page followed the browser and showed
the picker.

## Layout

```text
oxygen-dark-mode/
├── resources/
│   ├── dark-mode.js    ← pins data-wh-theme="dark" on <html>, pre-paint
│   └── dark-mode.css   ← hides the theme picker (.wh_theme)
└── page-templates-fragments/
    └── libraries/
        └── dark-mode.xml   ← a <head> fragment: one <script> tag
```

The folder names mirror the Fi3ldMan template so the files drop straight in.

## Wiring it into the (single, shared) template

1. **Use your existing publishing template** (the Fi3ldMan-derived one that
   hosts the GramFrame overlay — see `../gramframe-oxygen/README.md`).

2. **Copy `resources/dark-mode.js` and `resources/dark-mode.css`** into that
   template's `resources/` directory.

3. **Keep dark mode enabled in the template descriptor.** The template's dark
   palette is what this overlay selects, so leave (or add) the parameter that
   turns it on:

   ```xml
   <parameter name="webhelp.enable.dark.mode" value="yes"/>
   ```

   Setting it to `no` removes the theme menu from the generated markup (making
   the CSS below redundant), but it also switches off Oxygen's own dark-mode
   plumbing, and whether the template still emits its dark palette in that
   state is untested here. Leave it `yes` — the state this overlay was verified
   against — and let `dark-mode.css` hide the menu.

4. **Reference the CSS** from the `.opt`, inside `<resources>`, so it loads
   after the stock styles and wins the cascade:

   ```xml
   <resources>
     <!-- …existing entries (GramFrame bundle, hide-search.css, gram-nav.css,
          gram-toc-overlay.css, …)… -->
     <css file="resources/dark-mode.css"/>
   </resources>
   ```

5. **Wire the `<head>` fragment.** Copy `dark-mode.xml` into the template's
   `page-templates-fragments/libraries/` and map it in the `.opt` inside the
   `<html-fragments>` wrapper (add the wrapper if the `.opt` has none — it goes
   inside `<webhelp>`):

   ```xml
   <webhelp>
     <html-fragments>
       <!-- existing GramFrame entry -->
       <fragment file="page-templates-fragments/libraries/gramframe.xml"
                 placeholder="webhelp.fragment.head.topic.page"/>
       <!-- force-dark: ALL page types, not just topics -->
       <fragment file="page-templates-fragments/libraries/dark-mode.xml"
                 placeholder="webhelp.fragment.head"/>
     </html-fragments>
     …
   </webhelp>
   ```

   Use **`webhelp.fragment.head`** — it injects into the head of *every* page
   type (welcome, topic, search results, index terms), so the welcome page is
   dark too. It is a different placeholder from the GramFrame fragment's
   `webhelp.fragment.head.topic.page`, which matters: Oxygen binds **one**
   fragment per placeholder.

   > Prefer not to add a fragment file? Paste the one `<script>` line from
   > `dark-mode.xml` into the template's existing **all-pages** head fragment
   > instead. Don't paste it into the topic-page fragment — the welcome and
   > search pages would stay light.

6. **Point both scenarios at this template** — the instructor *and* student
   WebHelp Responsive scenarios share the one template, as they already do for
   the other overlays.

7. **Republish both editions and confirm:** every page (welcome, a gram topic,
   the search-results page) renders dark on first load with no light flash;
   there is no theme button in the header; and a browser set to *prefer light*
   still gets the dark output. If you had previously chosen "Light" in the
   menu, clear the site's local storage once to prove it — the page must come
   back dark regardless.

## Keeping the other overlays in step

`../gram-nav-panel/` was already dark-styled, so it needs nothing.
`../gram-toc-overlay/` floats the "On this page" mini-TOC on a light panel; it
now carries a `:root[data-wh-theme="dark"]` block that darkens that panel, so
the TOC links stay readable here. If you restyle either panel, restyle both.
`../gram-fill-width/` sets no colours at all — it only sizes the gram — so it
is theme-agnostic and needs nothing.



## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (alongside
the other overlays), so it lands at `ROOT\theme\oxygen-dark-mode\` on the
target. The operator installs it into the Oxygen template once, per steps 2–5
above. See README.md, *"Getting pipeline updates onto the target"*.

## Sources

- Dark mode and the `webhelp.enable.dark.mode` parameter (and the
  `:root[data-wh-theme="dark"]` contract):
  <https://www.oxygenxml.com/doc/versions/28.0/ug-webhelp-responsive/topics/webhelp-create-dark-mode-ready-publishing-template.html>
- `webhelp.fragment.head` — "display a given XHTML fragment in the header
  section in **all** types of pages":
  <https://www.oxygenxml.com/doc/ug-webhelp-responsive/topics/webhelp-responsive-plugin-additional-parameters.html>
- Adding custom CSS via a Publishing Template `.opt` `<css>` resource:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/webhelp-customizing-with-css.html>

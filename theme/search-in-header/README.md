# In-header search box for the Oxygen WebHelp Responsive template

A drop-in overlay that moves the WebHelp **search box into the header bar** and
sizes it as an ordinary header control, instead of leaving it as a full-width
band below the header. Like `../gram-nav-bar/` and `../gram-fill-width/`, it is
**not** a complete theme — it is one stylesheet, one small script and a
`<body>` fragment you add to your own Oxygen WebHelp Responsive template.

## The problem it fixes

Oxygen renders the search box as a **sibling of `<header>`**, not a child of it:

```html
<header class="navbar wh_header"> … title … top menu … </header>
<div class="wh_search_input navbar-form … search">
  <form id="searchForm"> … </form>
</div>
```

and the stock stylesheet gives that band `padding: 40px 0` plus a background
image — `115px 0` on the tiles landing page. So a control one input tall costs
roughly **120px of vertical space on every page**. On a gram page that is space
taken straight off the top of the spectrogram, which is the whole point of the
page (see `../gram-nav-bar/` and `../gram-fill-width/` for the same argument
applied to the right-hand column and the gram's own width).

The header, meanwhile, has room going spare: the publication title sits left,
the top menu right, and the theme picker that used to follow it is hidden by
`../oxygen-dark-mode/`.

## What it does

- `resources/search-in-header.js` moves `.wh_search_input` into the header's
  `.wh_top_menu_and_indexterms_link` — the collapsible group already holding
  the top menu — and stamps `wh_header_search` on `<header>`.
- `resources/search-in-header.css` strips the band's padding and background
  image and sizes the field as a header control (15em, 2.2em tall, full width
  on a narrow screen where the header stacks).

It applies to **every page type that has a search box**: the topic page, the
tiles landing page and the search-results page. The index-terms page has none,
and the script no-ops there.

## Why a script rather than CSS

The band is a **sibling** of `<header>`, and CSS cannot reparent an element.
Absolutely positioning it over the header instead would resolve against
`<body>` — the header is not the nearest positioned ancestor — and the
protective marking bar above it (`../oxygen-protection/`) makes the header's
offset a moving target. Reparenting is the honest version, and it gives the
stylesheet a marker class so nothing is half-restyled when JavaScript is off.

## Layout

```text
search-in-header/
├── page-templates-fragments/
│   └── libraries/
│       └── search-in-header.xml   ← loads the script inside the search band
└── resources/
    ├── search-in-header.css       ← sizes the moved box as a header control
    └── search-in-header.js        ← moves .wh_search_input into <header>
```

## The two editions

Nothing here is audience-aware. `../oxygen-hide-search/` decides whether the
box exists at all — hidden in the student edition, shown in the instructor's —
and it hides the **whole band**, so the student header carries no empty control
where this overlay would otherwise have put one.

## Wiring it into the (single, shared) template

> **Already wired in `../pptx-transform/`**, this repo's own publishing
> template — verbatim copies of both payload files and the fragment, the
> `<css>` entry and the `<fragment>` binding. Run `../sync.py` after editing a
> payload here. The steps below are for installing into a **different**
> template.

1. **Copy `resources/search-in-header.css` and `resources/search-in-header.js`**
   into the template's `resources/`, and
   `page-templates-fragments/libraries/search-in-header.xml` into its
   `page-templates-fragments/libraries/`.

2. **Reference the stylesheet** from `<resources>`, after the stock styles so
   it wins the cascade:

   ```xml
   <css file="resources/search-in-header.css"/>
   ```

3. **Bind the fragment** inside `<html-fragments>`:

   ```xml
   <fragment file="page-templates-fragments/libraries/search-in-header.xml"
             placeholder="webhelp.fragment.after.search.input"/>
   ```

   Oxygen binds **one fragment per placeholder**. `after.search.input` is
   deliberate — it is inside the band, after the header, on all three page
   types that have a search box. See the fragment's own comment for which
   placeholders this template has already spent, and the trap that
   `webhelp.fragment.header` / `.footer` are not free (they are how Oxygen
   pulls in `header.xml` and `footer.xml`).

4. **Republish and confirm:** the tall search band is gone from the top of
   every page; the search field sits in the header beside the top menu; typing
   a query and submitting still reaches the search-results page; the
   search-results page's own header search behaves the same; and at a narrow
   width the field goes full-width with the collapsed menu.

## Oxygen-only, like every overlay here

`.wh_search_input` and `.wh_header` are WebHelp Responsive chrome that exists
in no other renderer — `publish_html.py`'s DITA-OT preview emits neither, and
carries no stylesheet at all. Tune it against the committed Oxygen build;
`../sync.py` copies a CSS or JS edit straight into
`demo/oxygen-sample/published/` for a hard refresh, no republish. The fragment
binding, being a `.opt` change, does need one.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (alongside the
other overlays), so it lands at `ROOT\theme\search-in-header\` on the target.
The operator installs it into the Oxygen template once, per step 1 above. See
README.md, *"Getting pipeline updates onto the target"*.

## Sources

- HTML fragment placeholders in the WebHelp Responsive page templates:
  <https://www.oxygenxml.com/doc/versions/26.1/ug-webhelp-responsive/topics/whr-html-fragments.html>

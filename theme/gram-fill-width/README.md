# Full-width gram overlay for the Oxygen WebHelp Responsive template

A drop-in CSS overlay that makes each gram **consume the full width its column
offers**, instead of rendering at the spectrogram's natural pixel size and
leaving a band of whitespace down either side. Like `../gram-nav-panel/` and
`../gram-toc-overlay/`, it is **not** a complete theme — it is one CSS file you
add to your own Oxygen WebHelp Responsive template.

## The problem it fixes

It looks like the DITA wrapper is squeezing the component. It isn't. On the
target the content column is already full width —

```html
<div class="col-sm-10 col-xs-12 col-xxl-12 col-lg-12 col-md-9" id="wh_topic_body">
```

`col-xxl-12` / `col-lg-12` is 12 of 12, inside a Bootstrap `container-fluid`
that has no max-width cap. The whitespace is the **component** rendering at its
natural size and not claiming the rest:

```html
<div class="gram-frame-container" style="width: auto; height: auto; aspect-ratio: unset;">
  <svg class="gram-frame-svg" viewBox="0 0 971 438" style="width: 971px; height: 438px;">
    <image width="896" height="373">
```

That is deliberate in GramFrame, not a layout accident. `updateSVGLayout` sizes
the SVG from `getRenderDimensions()`, and `renderSize()` is
`renderWidth || naturalWidth` with `renderWidth` initialised to `0` — so it is
the natural size unless something sets it. The only thing that ever does is the
**Expand toggle**, whose `computeAvailableRenderSize()` is the sole place the
container's `clientWidth` is consulted. The component fills the width when the
reader clicks Expand, and not before.

The published training material wants that fill by **default**, without the
reader clicking Expand on every gram of every page.

## What it does

Overrides the two inline sizes the component writes on itself:

| Element | Inline (from `updateSVGLayout`) | This overlay |
| --- | --- | --- |
| `.gram-frame-container` | `width: auto` | `width: 100% !important` |
| `svg.gram-frame-svg` | `width: 971px; height: 438px` | `width: 100% !important; height: auto !important` |

`!important` is load-bearing and legitimately so: an important *author*
declaration outranks a normal *inline* one, which is what lets these rules
survive `updateSVGLayout` re-writing the inline styles on every relayout (zoom,
expand, window resize).

### `height: auto` is not optional

The SVG carries `viewBox="0 0 W H"` and `preserveAspectRatio="xMidYMid meet"`.
Widen it while its height stays pinned at the inline pixel value and `meet`
letterboxes the drawing inside the taller box — the gram would not actually
grow, **and the cursor readouts would go wrong**: `screenToSVG()` derives its
scale as `viewBox.width / rect.width`, which assumes the drawing fills the
element's box. `height: auto` lets the browser take the height from the
viewBox's intrinsic ratio, so the drawing fills the box and that holds.

## What it costs

The source spectrogram is a fixed-resolution PNG either way, so drawing it
wider upscales it — exactly as the Expand toggle's own re-render does. There is
no image quality lost *relative to expanding*.

What does differ: scaling the SVG scales its axes, tick labels and stroke
widths along with it, where Expand re-renders that chrome crisply at the new
size. The trade is deliberate — this is **width-only** and leaves the gram's
height alone, where Expand also grows each gram to fill the viewport height and
turns a nine-Lofar page into nine screens.

### The alternative, if you want the height too

`GramFrame.setExpandState(true)` is a public API that expands every landscape
instance. Called once after the bundle initialises, it gives the same width fill
*plus* the height fill, with crisply re-rendered chrome. It is not used here
because the height growth is a bigger behaviour change than the whitespace
complaint asked for.

## Scope

Keyed on `.gram-frame-container`, which the bundle only ever creates for a gram
it has upgraded — so unlike `../gram-toc-overlay/` there is nothing to scope to
gram pages. No other page has the class.

## Installing

**Already wired in `../pptx-transform/`**, this repo's own publishing template:
a verbatim copy sits at `resources/gram-fill-width.css` and the `.opt` loads it
from `<resources>`, after the stock styles so it wins the cascade. Point the
transformation scenario's **Templates** tab at `pptx-transform.opt` and publish.

Two tests guard it, because the two ways this can rot are different:
`tests/test_package_release.py` holds the template's copy byte-identical to this
file, and `tests/test_theme_gram_fill_width.py` checks the `.opt` still
references it — a payload copied in but never referenced does nothing at all.

To install into a **different** template, copy `resources/gram-fill-width.css`
into its `resources/` and add `<css file="resources/gram-fill-width.css"/>`
inside that `.opt`'s `<resources>`.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/`, so it lands at
`ROOT\theme\gram-fill-width\` on the target. See README.md, *"Getting pipeline
updates onto the target"*.

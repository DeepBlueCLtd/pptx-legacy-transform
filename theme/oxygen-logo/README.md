# Corporate logo, top left of the header (issue #196)

Oxygen WebHelp Responsive already supports a header logo through its own
`webhelp.logo.image` parameter — no page-layout fork or extra CSS is needed.
`theme/pptx-transform/pptx-transform.opt` declares:

```xml
<parameter name="webhelp.logo.image"
           value="resources/images/corporate-logo.png" type="filePath"/>
```

`type="filePath"` makes Oxygen resolve the relative value against the
template folder, so the template stays self-contained wherever it is
installed. Oxygen copies the image into the output and renders it at the left
of the header bar, linked to the publication's main page.

`resources/images/corporate-logo.png` is a **placeholder** (the Fi3ldMan
pub-5 logo, 120 × 62, transparent PNG — readable on the dark header).

## Changing the logo

Overwrite `resources/images/corporate-logo.png` (keep the name) and re-run
`theme/sync.py`; on the target, overwrite the same file in the installed
`theme\pptx-transform\resources\images\`.

**Do not** override `webhelp.logo.image` in a scenario's Parameters tab: that
puts a machine-local absolute path into every published page (see README.md,
"Create the instructor scenario").

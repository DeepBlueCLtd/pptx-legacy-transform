# `static/` — common pages for every publication

`generate_dita.py` copies this whole tree into **each** publication folder
under the DITA output root and references the top-level `*.dita` files as the
**first entries** on every generated ditamap — before the **Grams** navigation
folder that now holds the per-gram topics. The result: every published edition
opens with the same shared pages and a compact top-level nav
(**Welcome · Security · Grams**) instead of one nav entry per gram.

```
static/
├── welcome.dita     ← shown first  (id="welcome")
├── security.dita    ← shown second (id="security")
└── images/          ← assets the pages reference, copied verbatim
    └── welcome-banner.png
```

Conventions:

- **Order** — `welcome.dita` then `security.dita`; any further top-level
  `*.dita` you add follow alphabetically.
- **Self-contained hrefs** — keep image and cross-references *relative*
  (e.g. `images/welcome-banner.png`, `security.dita`). The pages are copied
  beside the ditamap, so relative hrefs resolve as authored; no `../`.
- **Edit in Oxygen** like any DITA topic. The files carry the OASIS DOCTYPE so
  Oxygen recognises them.

Override the location with `generate_dita.py --static-root <dir>` (default
`static/`). If the folder is missing, generation still succeeds — the ditamaps
simply carry no shared pages (a logged warning), consistent with the
"missing assets dangle, they don't crash" invariant.

> The content here is **mock development material** — replace `welcome.dita`
> and `security.dita` with the real pages before delivery.

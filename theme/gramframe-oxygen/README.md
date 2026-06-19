# GramFrame overlay for the Oxygen WebHelp Responsive template

A drop-in overlay that makes the **production Oxygen publish** render
interactive grams, exactly as `publish_html.py` already does for the dev/CI
HTML preview. It is **not** a complete theme — it is the two files (plus the
wiring) you add to your own Oxygen WebHelp Responsive template (the
Fi3ldMan-derived one).

## What it does

`generate_dita.py` emits every spectrogram as a `<table outputclass="gram-config">`
carrying the four parameter rows GramFrame expects. Oxygen passes `outputclass`
through to the HTML `@class`, so the published page has `<table class="gram-config">`.
Loading **`gramframe.bundle.js`** on that page upgrades each gram into an
interactive viewer; it no-ops on pages with no `gram-config` table. This is the
same contract `scripts/vendor/themes/operator-console-v2/README.md` calls out
under *"What the host must still do"*, item 3.

## Layout

```text
gramframe-oxygen/
├── resources/
│   ├── gramframe.bundle.js     ← the plugin (pinned, see VERSION)
│   └── VERSION                 ← which GramFrame release this is
└── page-templates-fragments/
    └── libraries/
        └── gramframe.xml       ← a <head> fragment: one <script> tag
```

The folder names mirror the Fi3ldMan template so the files drop straight in.

## Installing into your Oxygen template

1. **Copy the bundle** into your template's custom resources folder:

   ```text
   <your-template>/resources/gramframe.bundle.js
   ```

   Oxygen's `resources/**/*` fileset copies it to the output at
   `${oxygen-webhelp-assets-dir}/template/resources/gramframe.bundle.js` —
   the same place the template's other custom scripts (`sorttable.js`,
   `harmonics.js`, …) land.

2. **Load it from the topic page `<head>`.** Two options:

   - **Simplest — paste one line.** Add the `<script>` line from
     `page-templates-fragments/libraries/gramframe.xml` into your existing
     topic-page head fragment (in Fi3ldMan that is
     `page-templates-fragments/libraries/topic-page-libraries.xml`), beside the
     other `template/resources/*.js` scripts.

   - **Or wire the fragment file.** Copy `gramframe.xml` into your template's
     `page-templates-fragments/libraries/` and map it in your `.opt`, mirroring
     the existing fragment entry:

     ```xml
     <fragment file="page-templates-fragments/libraries/gramframe.xml"
               placeholder="webhelp.fragment.head.topic.page"/>
     ```

     Use a head placeholder that is **not already taken** by another fragment
     (Oxygen binds one fragment per placeholder).

3. **Publish a deck with at least one spectrogram gram, open the topic in a
   browser, and confirm** the static gram image upgrades to the interactive
   viewer — and that a page with no gram table is unaffected.

## Keep the bundle in sync

The bundle here is a copy of `scripts/vendor/gramframe/gramframe.bundle.js`
(see `resources/VERSION` — currently **v0.1.9**). They must stay byte-identical
so the Oxygen production output and the `publish_html.py` dev preview render
grams the same way; `tests/test_package_release.py` enforces this. When you bump
GramFrame, update **both** copies and the `VERSION` files together.

## How it ships to the air-gapped target

This overlay travels in the pipeline release zip under `theme/` (the only thing
under `theme/` today), so it lands at `ROOT\theme\gramframe-oxygen\` on the
target. The operator installs it into the Oxygen template once, per step 2
above. See README.md, *"Getting pipeline updates onto the target"*.

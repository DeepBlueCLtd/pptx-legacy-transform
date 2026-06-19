# Contract: Audience Filter

This document fixes the exact shape of the DITAVAL profile, the
audience-tagged elements in the DITA source tree, and the rendered-
HTML behaviour produced by applying the profile.

It is the authoritative reference for the test assertions in
`tests/test_generate_dita.py` and `tests/test_publish_html.py` that
cover SC-001, SC-002, SC-003, and FR-010 / FR-015.

## 1. DITAVAL profile

### 1.1 Location and filename

```
dita/trainee.ditaval
```

Path resolution: relative to the `--dita` argument of `publish_html.py`
(default: `dita/`). The publisher computes `<dita>/trainee.ditaval`
and passes that absolute path to DITA-OT's `--filter` flag for the
student edition.

### 1.2 File contents (byte-exact)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
</val>
```

- UTF-8, no BOM, LF line endings.
- Exactly one `<prop>` rule. Additional rules are out of scope for
  this feature.
- DITA-OT 4.x interprets this as: every element whose `audience`
  attribute contains the token `trainee` (DITA tokenises space-
  separated and `-`-prefixed values) is excluded from the build.

### 1.3 Build invocation

| Edition | DITA-OT invocation |
|---|---|
| instructor | `dita --input=<ditamap> --format=html5 --output=html/instructor/<stem>/ --processing-mode=lax` |
| student | `dita --input=<ditamap> --format=html5 --output=html/student/<stem>/ --processing-mode=lax --filter=<dita>/trainee.ditaval` |

The only CLI difference between the two editions is the `--filter`
argument and the `--output` destination.

## 2. Audience-tagged elements in the DITA source

### 2.1 Sites carrying `audience="-trainee"`

| # | Site | Element form | Owner |
|---|---|---|---|
| 1 | Vessel-name decoration on a gram title | `<title>Gram NN<ph audience="-trainee"> — vessel</ph></title>` | feature 001 (`emit_gram_topic`) |
| 2 | Analysis Sheet section on a gram body | `<section audience="-trainee"><title>Analysis Sheet</title>…</section>` | feature 001 (`_append_analysis_section`) |
| 3 | Chapter navtitle prefix on `main.ditamap` | `<topichead><topicmeta><navtitle><ph audience="-trainee">Instructor </ph>Week 1 Grams</navtitle></topicmeta></topichead>` | this feature (`emit_main_ditamap`) |
| 4 | Map title suffix on every ditamap | `<map><title>Progress Test 1<ph audience="-trainee"> — Instructor Version</ph></title>…</map>` | this feature (`emit_main_ditamap`, `emit_test_ditamap`) |
| 5 | Hidden edition marker on every page body | `<body><p audience="-trainee" outputclass="edition-instructor"/>…</body>` | `_append_edition_marker` / `_inject_static_edition_marker` |

Site 5 fires on **every** rendered page: every gram topic, every Week
sub-document topic, and the copied static common pages (Welcome,
Security). It is the per-page edition signal a single shared Oxygen
stylesheet keys off (present → instructor, absent → student) so the
WebHelp search box can be hidden in the student edition without a
divergent student-only publishing template. The marker renders as
`<p class="edition-instructor">` and is hidden by CSS; the class string
only ever appears in instructor output, so SC-002 stays clean.

Site 3 only fires for chapters whose CSV `chapter` column starts
(case-insensitive) with `"Instructor "`; chapters without that prefix
emit a plain `<navtitle>Plain Chapter</navtitle>` with no `<ph>`
wrapper.

Site 4 fires for **every** ditamap, regardless of source title.

### 2.2 Forbidden shapes

The following shapes MUST NOT appear in the DITA source tree this
feature emits:

- `<map title="…">` with the `title=` attribute present (replaced by
  the `<title>` child element — R2).
- `<topichead navtitle="…">` with the `navtitle=` attribute present
  (replaced by `<topicmeta>/<navtitle>` — R3).
- Any topic filename or chapter-folder slug containing the substring
  `"instructor"` (case-insensitive) — FR-014.

## 3. Rendered-HTML behaviour

### 3.1 Instructor edition (no filter)

| Source site | Rendered HTML behaviour |
|---|---|
| Site 1 | Gram heading reads `"Gram NN — vessel"`. |
| Site 2 | Analysis Sheet section renders as a normal `<section>` with the link or embedded image. |
| Site 3 | Chapter navigation entry reads `"Instructor Week 1 Grams"`. |
| Site 4 | Page title / breadcrumb reads `"Progress Test 1 — Instructor Version"`. |
| Site 5 | `<p class="edition-instructor">` present (hidden by CSS); `body:not(:has(.edition-instructor))` does not match, so the search box stays visible. |

### 3.2 Student edition (`--filter=dita/trainee.ditaval`)

| Source site | Rendered HTML behaviour |
|---|---|
| Site 1 | The `<ph>` element is stripped; the gram heading reads `"Gram NN"` with no trailing separator. |
| Site 2 | The entire `<section>` is stripped; no "Analysis Sheet" heading and no link / image is rendered. |
| Site 3 | The `<ph>` element is stripped; the chapter navigation entry reads `"Week 1 Grams"`. |
| Site 4 | The `<ph>` element is stripped; page title / breadcrumb reads `"Progress Test 1"`. |
| Site 5 | The `<p>` marker is stripped; `body:not(:has(.edition-instructor))` matches, so the search box is hidden. |

### 3.3 Leakage guarantee (SC-002, FR-010, FR-015)

A full-text grep over every file under `html/student/` MUST return
zero matches for the case-insensitive substring `"instructor"`,
checking:

- File contents (every `*.html`, `*.css`, `*.js` if any).
- File paths (every directory and file name).
- The shared `html/index.html` is checked separately and IS permitted
  to contain the word "Instructor" because it links to (and labels)
  the instructor edition.

### 3.4 URL parity (FR-016)

For every relative path `P` that exists under `html/instructor/`,
the file `html/student/P` MUST exist (and vice versa). The two
files differ only in the content the audience filter strips.

This is checked by enumerating one tree's files, mapping the
edition segment, and asserting `exists()` on the other tree.

## 4. Idempotency (FR-008 / SC-006)

Two consecutive invocations of `publish_html.py` against the same
DITA source tree MUST produce byte-identical files under `html/` in
both editions.

The publisher's post-render pass (today: `prettify_tree()`) is
extended to scrub any non-deterministic metadata DITA-OT emits — in
particular any `<meta name="DC.date.created">` element and any
DITA-OT generated-on comment — so the byte-for-byte comparison holds
(R7).

A hash-of-tree comparison test in `tests/test_publish_html.py` runs
the publisher twice in a temp dir and asserts equality.

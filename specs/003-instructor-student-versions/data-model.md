# Phase 1 Data Model: Instructor / Student Versions via DITA Audience Filtering

**Feature**: Instructor / Student Versions via DITA Audience Filtering
**Date**: 2026-05-16

This feature has no database. Its data model is the cross-product of
two new concepts (*Edition*, *DITAVAL profile*) with the entities
feature 001 already defined (*Publication*, *Gram topic*,
*Audience-tagged element*), plus a handful of in-memory records used
inside `generate_dita.py` and `publish_html.py`.

---

## 1. Editions

### 1.1 `Edition` (in-memory, `publish_html.py`)

A single named HTML rendering of every publication for one audience.

| Field | Type | Source | Notes |
|---|---|---|---|
| `name` | `str` | hard-coded | `"instructor"` or `"student"` |
| `output_subdir` | `pathlib.Path` | derived from `name` | `html/instructor/` or `html/student/` |
| `ditaval` | `pathlib.Path \| None` | hard-coded | `dita/trainee.ditaval` for student, `None` for instructor |
| `description` | `str` | hard-coded | one-sentence audience description for the shared landing page |

**Cardinality**: Exactly two editions per publish run. No mechanism to
extend the set at runtime (FR-013 / Out of Scope: no further
audiences).

**Validation**:

- The instructor edition's `ditaval` MUST be `None` (the unfiltered
  superset).
- The student edition's `ditaval` MUST point at an existing file under
  `dita/`; if the file is missing the publisher exits non-zero.

### 1.2 `LandingPage` (in-memory, `publish_html.py`)

The shared top-level `html/index.html`.

| Field | Type | Source | Notes |
|---|---|---|---|
| `editions` | `list[Edition]` | populated by the publisher | always exactly two |
| `generated_at` | `str` | `SOURCE_DATE_EPOCH` or fixed default | deterministic timestamp (R6) |

**Validation**: `len(editions) == 2`. The page's link order is
deterministic (instructor first, student second) so the HTML is
byte-stable.

---

## 2. DITAVAL profile

### 2.1 `dita/trainee.ditaval`

A single static file committed alongside the DITA source tree.
Filename and location are fixed (R10).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
</val>
```

| Property | Value | Notes |
|---|---|---|
| `att` | `audience` | the DITA attribute the filter inspects |
| `val` | `trainee` | the audience value to act on |
| `action` | `exclude` | strip every element whose `audience` contains `trainee` |

DITA-OT interprets `audience="-trainee"` in the DITA source as
"element is for everyone EXCEPT trainees"; with the rule above,
elements carrying that attribute value are excluded from the trainee
build. Elements without an `audience` attribute are unaffected.

---

## 3. Audience-tagged elements (DITA-side, extends feature 001)

This feature does not change any element shape feature 001 already
introduced; it adds two new sites that must carry the audience tag:

| Site | Element form | Carries `audience="-trainee"` on… |
|---|---|---|
| **Gram title vessel-name decoration** | `<title>Gram NN<ph audience="-trainee"> — vessel</ph></title>` | the inline `<ph>` (already shipped by feature 001) |
| **Analysis Sheet section** | `<section audience="-trainee"><title>Analysis Sheet</title>…</section>` | the `<section>` element itself (already shipped by feature 001) |
| **Chapter navtitle prefix** (NEW) | `<topichead><topicmeta><navtitle><ph audience="-trainee">Instructor </ph>Week 1 Grams</navtitle></topicmeta></topichead>` | the inline `<ph>` wrapping the leading `"Instructor "` substring |
| **Map title suffix** (NEW) | `<map><title>Progress Test 1<ph audience="-trainee"> — Instructor Version</ph></title>…</map>` | the inline `<ph>` wrapping the `" — Instructor Version"` suffix |

The first two are already wired up in `generate_dita.py`
(`emit_gram_topic`, `_append_analysis_section`); the last two are
introduced by this feature inside `emit_main_ditamap` and
`emit_test_ditamap`.

### 3.1 Separator character on the gram title decoration

The vessel-name decoration's leading separator MUST NOT be a colon
(FR-003). The decoration text is `" — vessel_name"` (space + em-dash
+ space + name) — already the case in the source today, recorded
here for completeness and to pin the test assertion.

---

## 4. Chapter-string normalisation

### 4.1 `ChapterNormalisation` (in-memory, `generate_dita.py`)

A small dataclass-shaped record computed once per chapter on its way
through the ditamap emitter.

| Field | Type | Source | Notes |
|---|---|---|---|
| `raw` | `str` | CSV `chapter` column | exactly as supplied by the extractor |
| `audience_prefix` | `str \| None` | `"Instructor "` if `raw` starts with it (case-insensitive); else `None` | preserves source casing |
| `display_remainder` | `str` | `raw` with `audience_prefix` stripped | the audience-neutral part of the navtitle |
| `slug` | `str` | `slugify(display_remainder)` | the chapter folder name; never contains "instructor" |

**Examples**:

| `raw` | `audience_prefix` | `display_remainder` | `slug` |
|---|---|---|---|
| `"Instructor Week 1 Grams"` | `"Instructor "` | `"Week 1 Grams"` | `"week-1-grams"` |
| `"Instructor Pub10_Ed22B_Updated"` | `"Instructor "` | `"Pub10_Ed22B_Updated"` | `"pub10-ed22b-updated"` |
| `"Plain Chapter Without Prefix"` | `None` | `"Plain Chapter Without Prefix"` | `"plain-chapter-without-prefix"` |
| `""` | `None` | `""` | `""` |

**Validation**: `slug` is the only string used to construct file paths
under `dita/` and `html/`; `display_remainder` is the only string
used to construct the audience-neutral text of the rendered
`<navtitle>`. The audience prefix never reaches the slug computation.

---

## 5. Ditamap shape (extends feature 001)

### 5.1 `main.ditamap` — after this feature

```xml
<map>
  <title>Main<ph audience="-trainee"> — Instructor Version</ph></title>
  <topichead>
    <topicmeta>
      <navtitle><ph audience="-trainee">Instructor </ph>Week 1 Grams</navtitle>
    </topicmeta>
    <topicref href="main/week-1-grams/gram-01/gram_01.dita"/>
    <!-- …one topicref per gram in CSV order… -->
  </topichead>
  <!-- …further chapters… -->
</map>
```

Notes:

- The `<map>` element NO LONGER carries the `title=` attribute. The
  publication title lives entirely inside the `<title>` child element.
- The `<topichead>` element NO LONGER carries the `navtitle=`
  attribute. The chapter navtitle lives entirely inside the
  `<topicmeta>/<navtitle>` child.
- The chapter folder path under `topicref/@href` uses the normalised
  slug (`week-1-grams`, not `instructor-week-1-grams`).

### 5.2 `progress-test-N.ditamap` — after this feature

```xml
<map>
  <title>Progress Test N<ph audience="-trainee"> — Instructor Version</ph></title>
  <topicref href="progress-test-N/gram-NN/gram_NN.dita"/>
  <!-- …one topicref per gram, flat… -->
</map>
```

Progress-test ditamaps still have no `<topichead>` (FR-012 from
feature 001 still applies). The map title gains the audience-tagged
suffix.

---

## 6. Output tree shape (extends feature 001's §9)

### 6.1 `html/` after a publish run

```text
html/
├── index.html                       # shared landing (LandingPage)
├── instructor/
│   ├── index.html                   # per-edition publication index
│   ├── main/                        # DITA-OT output for main.ditamap, no filter
│   │   ├── index.html
│   │   └── …
│   ├── progress-test-1/             # DITA-OT output, no filter
│   │   └── …
│   └── …
└── student/
    ├── index.html                   # per-edition publication index
    ├── main/                        # DITA-OT output for main.ditamap, --filter=dita/trainee.ditaval
    │   └── …
    ├── progress-test-1/             # DITA-OT output, --filter=…
    │   └── …
    └── …
```

URL parity rule: for every path P under `html/instructor/`, the path
obtained by replacing `instructor/` with `student/` MUST exist under
`html/student/` and refer to the same gram (its content differs by
the audience filter only). FR-016.

### 6.2 `dita/` after `generate_dita.py` runs

```text
dita/
├── trainee.ditaval                  # NEW (this feature)
├── main.ditamap                     # MODIFIED shape (R2, R3)
├── main/
│   ├── week-1-grams/                # NEW slug (was instructor-week-1-grams/)
│   │   └── gram-NN/
│   │       └── gram_NN.dita
│   ├── pub10-ed22b-updated/         # NEW slug
│   │   └── …
│   └── …
├── progress-test-1.ditamap          # MODIFIED shape (R2)
├── progress-test-1/
│   └── …
└── …
```

Gram topic shape is unchanged from feature 001. The audience-tagged
content inside each gram topic (vessel-name `<ph>`, Analysis Sheet
`<section>`) is unchanged.

---

## 7. State transitions

This feature is stateless at runtime — each publish invocation is a
fresh deterministic transform of inputs (DITA source + DITAVAL
profile) to outputs (`html/` tree). There are no per-edition flags,
caches, or persisted run state.

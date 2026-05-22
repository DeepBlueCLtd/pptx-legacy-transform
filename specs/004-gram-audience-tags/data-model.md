# Phase 1 Data Model: Per-Gram Audience Tags via CSV `audience` Column

**Feature**: Per-Gram Audience Tags via CSV `audience` Column
**Date**: 2026-05-22

This feature has no database. Its data model is one new CSV column,
one new DITA attribute site, two new DITAVAL profiles, and the
extension of feature 003's two editions into three. Everything
below is either an in-memory shape inside one of the four edited
scripts or a serialised artefact (CSV cell, DITA attribute, DITAVAL
file) that travels between them.

---

## 1. CSV — new `audience` column

### 1.1 Column position and header

The CSV gains a 16th column appended after `warnings`. The full
header row becomes:

```text
publication,chapter,gram_id,vessel_name,topic_type,sequence,topic_filename,display_text,link_href,glc_path,time_end,freq_end,png_path,wav_treatment,warnings,audience
```

(Feature 004 also drops the stale `analysis_docx_path` column from
the csv-schema.md contract — it was documented at position 14 but
has never appeared in extractor output. The actual baseline has 15
columns; `audience` appends as the 16th.)

### 1.2 Cell semantics

| Property | Value |
|---|---|
| Column name | `audience` |
| Position | 16 (last; appended after `warnings`) |
| Type | string |
| Empty allowed? | yes (the default for every gram with no PPTX tag) |
| Canonical form | hyphen-prefixed audience tokens, space-separated, no leading/trailing whitespace, single spaces between tokens |
| Examples | `""`, `"-own"`, `"-other"`, `"-own -other"`, `"-other -own"` |

### 1.3 Per-gram consistency rule

All CSV rows that share a `(publication, chapter, gram_id)` key MUST
carry the same `audience` cell value (FR-004). The extractor produces
identical values across the rows of one gram by construction (it
parses the descriptor once and writes the value into every emitted
row). The generator enforces the rule on read by grouping rows by
`(publication, chapter, gram_id)` and asserting that the set of
distinct `audience` values across the group has exactly one element.

When the assertion fails, the generator raises a named exception
naming the publication, chapter, gram_id, and the conflicting values
(SC-007).

### 1.4 Backward compatibility (15-column legacy CSV)

A CSV without the `audience` column reads as if every row had an
empty 16th cell. The generator's column-count check accepts both 15
and 16 columns; the writer always emits 16.

---

## 2. PPTX descriptor — extraction rule

### 2.1 Source shape

PPTX grams place a descriptor in their slide's header text run:

```text
Gram N: <vessel detail> [<tag1>][<tag2>]…
```

Whitespace between bracketed groups is optional. The left side of
the colon (`Gram N`) is unchanged by this feature. Only the right
side may carry trailing bracketed groups.

### 2.2 Extractor parsing (extends `_split_descriptor` in
`extract_to_csv.py`)

```python
def _split_descriptor(descriptor: str) -> tuple[str, str, str]:
    """Return (gram_id, vessel_name, audience)."""
    if not descriptor:
        return ("", "", "")
    left, sep, right = descriptor.partition(":")
    gram_id = _canonicalise_gram_id(left.strip())
    right = right.strip() if sep else ""
    head, audience = _strip_audience_tags(right)
    return (gram_id, head.strip(), audience)


def _strip_audience_tags(text: str) -> tuple[str, str]:
    """Strip trailing [xxx] groups; return (head, audience)."""
    tags: list[str] = []
    pattern = re.compile(r"\s*\[([^\[\]]+)\]\s*$")
    while True:
        m = pattern.search(text)
        if not m:
            break
        tags.append(m.group(1).strip())
        text = text[: m.start()].rstrip()
    # tags were appended right-to-left; reverse to source order.
    tags.reverse()
    audience = " ".join(t for t in tags if t)
    return (text, audience)
```

The function's third return value flows into the new `audience` CSV
cell for every row the gram emits.

### 2.3 Examples

| descriptor | `gram_id` | `vessel_name` | `audience` |
|---|---|---|---|
| `"Gram 7: FR Vessel, Category 1, Bespin"` | `"7"` | `"FR Vessel, Category 1, Bespin"` | `""` |
| `"Gram 7: FR Vessel, Category 1, Bespin [-own]"` | `"7"` | `"FR Vessel, Category 1, Bespin"` | `"-own"` |
| `"Gram 7: FR Vessel [-own][-other]"` | `"7"` | `"FR Vessel"` | `"-own -other"` |
| `"Gram 7: FR Vessel [-own] [-other]"` | `"7"` | `"FR Vessel"` | `"-own -other"` |
| `"Gram 7: [-other]"` | `"7"` | `""` | `"-other"` |
| `"Gram 7"` (no colon) | `"7"` | `""` | `""` |

---

## 3. DITA — `audience` attribute on `<topicref>` (NEW site)

### 3.1 Emission rule

For each gram, the DITA generator emits a `<topicref>` element
inside the gram's parent map element (`<map>` for progress-test
ditamaps; `<topichead>` for the per-chapter group inside
`main.ditamap`). When the gram's `audience` value is non-empty, the
generator adds an `audience="…"` attribute on that topicref with the
value verbatim (after the whitespace normalisation in §1.2). When the
value is empty, no `audience` attribute is emitted (not
`audience=""`).

### 3.2 Examples

```xml
<!-- Empty audience cell → no attribute -->
<topicref href="progress-test-3/gram-09/gram_09.dita"/>

<!-- audience="-own" -->
<topicref href="progress-test-3/gram-10/gram_10.dita" audience="-own"/>

<!-- audience="-other" -->
<topicref href="progress-test-3/gram-11/gram_11.dita" audience="-other"/>

<!-- audience="-own -other" -->
<topicref href="progress-test-3/gram-12/gram_12.dita" audience="-own -other"/>
```

### 3.3 Non-propagation rule

The per-gram audience value is emitted on the topicref **only**. It
is NOT propagated to:

- The gram's `<topic>` root element.
- Any element inside the gram's topic file.
- The parent `<topichead>` (chapter) or `<map>` (publication).

This is the deliberate index-only-filter shape from R3 / FR-006: a
reader who navigates to the gram via a direct URL — bypassing the
index — sees the unfiltered topic in any edition.

### 3.4 Coexistence with feature 003's `-trainee` tags

The `-trainee` tags introduced by feature 003 remain on the same
DOM sites (inline `<ph>` for vessel-name decoration, `<section>` for
the analysis sheet, `<ph>` for chapter-navtitle prefix, `<ph>` for
map-title suffix). The new `-own` / `-other` tags live exclusively
on topicrefs; the two namespaces do not overlap. A gram tagged
`-own` whose topic also contains `audience="-trainee"` on its inner
`<ph>` is filtered as follows:

- Instructor edition (no DITAVAL filter): topicref visible, topic
  rendered with all inner content.
- Student-own edition (DITAVAL excludes `-trainee` AND `-own`):
  topicref is filtered out → topic is not emitted at all → the
  `-trainee` filter applied to the topic body is moot.
- Student-other edition (DITAVAL excludes `-trainee` AND `-other`):
  topicref is included (not `-other`) → topic is emitted → the
  `-trainee` filter strips the vessel-name `<ph>` and the analysis
  `<section>` from the topic body as before.

---

## 4. DITAVAL profiles (generator-emitted)

All three DITAVAL files are emitted by `generate_dita.py` into its
output directory (the dita staging tree) — none are committed
source files. The function `write_trainee_ditaval` (feature 003) is
renamed `write_ditaval_profiles` and writes all three in one pass.

### 4.1 `<dita-out>/student-own.ditaval` (NEW)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
  <prop att="audience" val="own" action="exclude"/>
</val>
```

Used by `publish_html.py` when rendering the `student-own` edition.

### 4.2 `<dita-out>/student-other.ditaval` (NEW)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
  <prop att="audience" val="other" action="exclude"/>
</val>
```

Used by `publish_html.py` when rendering the `student-other` edition.

### 4.3 `<dita-out>/trainee.ditaval` (UNCHANGED in shape)

Same `<prop>` rule as feature 003 (excludes `audience='trainee'`).
Now emitted alongside the two new profiles by
`write_ditaval_profiles` rather than by a function dedicated to it.
Not directly referenced by this feature's publisher invocations
(the trainee rule is composed into the two student-* profiles
above), but kept in place so the feature-003 contract still
resolves on read.

| Property | Value | Notes |
|---|---|---|
| `att` | `audience` | the DITA attribute the filter inspects |
| `val` | `trainee` / `own` / `other` | the audience value to act on |
| `action` | `exclude` | strip every element whose `audience` contains the named value |

---

## 5. Editions (extends feature 003's §1)

### 5.1 `Edition` (in-memory, `publish_html.py`)

A single named HTML rendering of every publication for one audience.

| Field | Type | Source | Notes |
|---|---|---|---|
| `name` | `str` | hard-coded | `"instructor"`, `"student-own"`, or `"student-other"` |
| `output_subdir` | `pathlib.Path` | derived from `name` | `html/instructor/`, `html/student-own/`, or `html/student-other/` |
| `ditaval` | `pathlib.Path \| None` | hard-coded | `None` for instructor; `<dita-out>/student-own.ditaval` for student-own; `<dita-out>/student-other.ditaval` for student-other (resolved against the dita staging tree at publish time) |
| `description` | `str` | hard-coded | one-sentence audience description for the shared landing page |

**Cardinality**: Exactly three editions per publish run, in the
order `[instructor, student-own, student-other]` so the shared
landing page is byte-stable.

**Validation**:

- The instructor edition's `ditaval` MUST be `None`.
- Each student-* edition's `ditaval` MUST point at an existing file
  under the dita staging tree (written by
  `write_ditaval_profiles`); if either is missing the publisher
  exits non-zero.

### 5.2 `LandingPage` (in-memory, `publish_html.py`)

The shared top-level `html/index.html`.

| Field | Type | Source | Notes |
|---|---|---|---|
| `editions` | `list[Edition]` | populated by the publisher | always exactly three, in fixed order |
| `generated_at` | `str` | `SOURCE_DATE_EPOCH` or fixed default | deterministic timestamp (feature 003 R6) |

---

## 6. Output tree shape

### 6.1 `html/` after a publish run

```text
html/
├── index.html                       # shared landing (LandingPage, three links)
├── instructor/                      # unchanged from feature 003
│   ├── index.html
│   ├── main/
│   │   └── …
│   ├── progress-test-1/
│   │   └── …
│   └── …
├── student-own/                     # NEW
│   ├── index.html
│   ├── main/
│   │   └── …
│   ├── progress-test-3/             # the substitution case
│   │   └── …                        # gram tagged `-own` is absent from index
│   └── …
└── student-other/                   # NEW
    ├── index.html
    ├── main/
    │   └── …
    ├── progress-test-3/
    │   └── …                        # gram tagged `-other` is absent from index
    └── …
```

URL parity within each edition is preserved exactly as feature 003
specified: any path P that exists under `html/instructor/<edition>`
and survives the edition's filter also exists at the same path
under `html/<edition>/`. (The two student editions differ in *which*
grams survive — one excludes the `-own` gram, the other excludes the
`-other` gram — but the surviving grams sit at the same paths.)

### 6.2 `dita/` staging tree after `generate_dita.py` runs

All three DITAVAL profiles are emitted by `write_ditaval_profiles`
into the same output directory as the ditamaps. The staging tree is
fully reproduced from inputs on every run — none of these files are
committed.

```text
dita/                                # generator's output directory
├── trainee.ditaval                  # emitted (rule unchanged from feature 003)
├── student-own.ditaval              # NEW — emitted
├── student-other.ditaval            # NEW — emitted
├── main.ditamap                     # MODIFIED (topicrefs may carry audience=…)
├── main/
│   └── …                            # gram topics unchanged
├── progress-test-3.ditamap          # MODIFIED — Week 3 grams 9/10 carry audience=
├── progress-test-3/
│   └── …                            # gram topics unchanged
└── …
```

Gram topic shape is unchanged from features 001 / 003. The audience-
tagged content inside each gram topic (vessel-name `<ph>`, Analysis
Sheet `<section>`) is unchanged.

---

## 7. Mock corpus changes (`mock_pptx.py`)

### 7.1 `PUBLICATIONS` tuple

Remove the entry:

```python
Publication("Instructor Progress Test 3 Grams No FR", FAMILY_TEST, no_fr=True),
```

The remaining 10 publications stay as-is.

### 7.2 Audience-tag planting

The descriptor builder for `Instructor Week 3 Grams` emits `[-own]`
on the last gram of the second slide (slide index 1, last gram) and
`[-other]` on the second-to-last gram of the second slide. The
choice is keyed to gram index, not RNG draw, so the planted tags
are deterministic regardless of seed.

In code terms (sketch — exact wording is implementation):

```python
if pub.name == "Instructor Week 3 Grams" and gram_position_on_slide_2 == "last":
    descriptor = f"{descriptor} [-own]"
elif pub.name == "Instructor Week 3 Grams" and gram_position_on_slide_2 == "second-last":
    descriptor = f"{descriptor} [-other]"
```

---

## 8. State transitions

This feature is stateless at runtime — each publish invocation is a
fresh deterministic transform of inputs (CSV + DITA source + DITAVAL
profiles) to outputs (`html/` tree). There are no per-edition flags,
caches, or persisted run state.

The only stateful artefact is `source.csv` itself, which carries the
author's hand-edits to the `audience` column between PPTX
re-extractions. The author's edits to the audience column are
preserved across a re-extraction *only if the author edits the CSV
after the latest extraction*; re-running the extractor regenerates
the CSV from PPTX and overwrites the cell. This is identical to how
every other CSV cell behaves today (the CSV is the human-review
seam, not a long-term editable store).

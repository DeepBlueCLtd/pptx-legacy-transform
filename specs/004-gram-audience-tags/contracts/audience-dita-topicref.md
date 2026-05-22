# Contract: DITA Topicref `audience` Attribute + DITAVAL Profiles

**Feature**: Per-Gram Audience Tags via CSV `audience` Column
**Status**: Draft

This contract defines the DITA-side emission site for the per-gram
audience value, the two new DITAVAL profiles, and the rules
DITA-OT applies at build time.

## 1. Emission site

The per-gram `audience` value is emitted as an `audience="…"`
attribute on the `<topicref>` element inside the gram's parent
ditamap container:

- For `progress-test-N` ditamaps: the immediate `<topicref>` child
  of `<map>`.
- For `main.ditamap`: the `<topicref>` child of the chapter's
  `<topichead>` group.

Concrete examples:

```xml
<!-- progress-test-3.ditamap (excerpt) -->
<map>
  <title>Progress Test 3<ph audience="-trainee"> — Instructor Version</ph></title>
  <topicref href="progress-test-3/gram-08/gram_08.dita"/>
  <topicref href="progress-test-3/gram-09/gram_09.dita" audience="-own"/>
  <topicref href="progress-test-3/gram-10/gram_10.dita" audience="-other"/>
</map>
```

```xml
<!-- main.ditamap (excerpt, Week 3 chapter) -->
<topichead>
  <topicmeta>
    <navtitle><ph audience="-trainee">Instructor </ph>Week 3 Grams</navtitle>
  </topicmeta>
  <topicref href="main/week-3-grams/gram-08/gram_08.dita"/>
  <topicref href="main/week-3-grams/gram-09/gram_09.dita" audience="-own"/>
  <topicref href="main/week-3-grams/gram-10/gram_10.dita" audience="-other"/>
</topichead>
```

## 2. Attribute emission rules

| CSV `audience` cell | Emitted attribute |
|---|---|
| `""` (empty) | no `audience` attribute on the topicref |
| `"-own"` | `audience="-own"` |
| `"-other"` | `audience="-other"` |
| `"-own -other"` | `audience="-own -other"` |
| `"  -own   -other  "` (non-canonical whitespace) | `audience="-own -other"` (normalised) |
| `"-foo"` (unrecognised token) | `audience="-foo"` + WARNING logged |
| `"own"` (include-style token) | build fails with named error |

The attribute value is the whitespace-normalised CSV cell value.
The generator never emits `audience=""` — an empty value means the
attribute is omitted entirely.

## 3. Non-propagation rule

The per-gram audience value is emitted on the topicref ONLY. The
generator MUST NOT:

- Set an `audience` attribute on the gram's `<topic>` element.
- Set an `audience` attribute on any inner element of the topic
  (e.g. `<title>`, `<body>`, `<section>`, `<ph>`).
- Set an `audience` attribute on the parent `<topichead>` or `<map>`.

The `-trainee` tags introduced by feature 003 inside the topic body
(vessel-name `<ph>`, analysis `<section>`) and inside the ditamap's
chrome (`<navtitle>` prefix, `<title>` suffix) are unaffected by
this feature — they continue to be emitted at exactly the same
sites in exactly the same shape.

## 4. DITAVAL profiles

### 4.1 `dita/trainee.ditaval` (UNCHANGED)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
</val>
```

Carried over verbatim from feature 003. Not directly used by this
feature's publisher invocations (its rule is composed into the two
student-* profiles), but committed so the feature-003 contract
still resolves on read.

### 4.2 `dita/student-own.ditaval` (NEW)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
  <prop att="audience" val="own" action="exclude"/>
</val>
```

Excludes every element whose `audience` attribute contains the
`trainee` token OR the `own` token (DITA-OT treats multiple rules
inside one `<val>` as logical OR).

### 4.3 `dita/student-other.ditaval` (NEW)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
  <prop att="audience" val="other" action="exclude"/>
</val>
```

### 4.4 Token vs. attribute value

The DITA source emits audience tokens with a leading hyphen
(`audience="-own"`). The DITAVAL `val=` attribute names the bare
token without the hyphen (`val="own"`). DITA-OT's filter logic
interprets the leading hyphen in the DITA attribute as a negative
match marker: an element carrying `audience="-own"` is *excluded*
when a DITAVAL profile names `own` with action `exclude`. The
hyphen and the profile-side action together produce the exclude
behaviour.

This convention is inherited from feature 003 and remains the
single audience-attribute style across the whole feature family.

## 5. DITA-OT invocation per edition

The publisher invokes DITA-OT once per (publication, edition) pair:

| Edition | `--filter` argument |
|---|---|
| `instructor` | (omitted) |
| `student-own` | `--filter=dita/student-own.ditaval` |
| `student-other` | `--filter=dita/student-other.ditaval` |

A publication that has 0 audience-tagged grams produces three
identical-content output trees (the filter is a no-op when nothing
matches). A publication with N audience-tagged grams produces
three output trees that differ in exactly which gram pages are
emitted.

## 6. Filter effect at build time

For each gram's `<topicref>`:

- **Instructor edition**: every topicref is included; every topic
  is emitted; the audience-tagged content *inside* each topic is
  rendered with no filtering applied.
- **Student-own edition**: a topicref carrying `audience="-own"`
  (or `audience` value containing `-own`) is excluded; its topic
  is not emitted under `html/student-own/`. A topicref with no
  `audience` attribute, or with `audience="-other"` only, is
  included; its topic is emitted with the `-trainee` filter applied
  to inner content (vessel-name `<ph>` stripped, analysis
  `<section>` stripped).
- **Student-other edition**: symmetric — `-other` topicrefs
  excluded, `-own` and untagged topicrefs included.

A topicref carrying `audience="-own -other"` is excluded from both
student editions. A topicref carrying any unrecognised token (e.g.
`-foo`) is included in every student edition (the unrecognised
token doesn't match any DITAVAL rule).

## 7. Idempotency

The per-gram audience attribute does not introduce new sources of
non-determinism. The attribute value is derived deterministically
from the CSV cell, the topicref emission order is the CSV iteration
order (already deterministic per feature 001), and DITA-OT's per-
edition output stays byte-stable when the prettifier strips/stamps
its build-time metadata (feature 003 R7).

Two consecutive publish runs over the same CSV → DITA → HTML chain
produce byte-identical output in all three edition subtrees
(FR-014 / SC-004).

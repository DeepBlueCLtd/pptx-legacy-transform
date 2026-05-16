# Phase 0 Research: Instructor / Student Versions via DITA Audience Filtering

**Feature**: Instructor / Student Versions via DITA Audience Filtering
**Date**: 2026-05-16

This document records the decisions taken to resolve the technical
unknowns the spec left implicit, and the best-practice choices for each
DITA / DITA-OT mechanism the feature depends on. The DITA source tree
must stay single-rooted (FR-013) and idempotent (FR-008 / SC-006), so
several decisions trade flexibility for byte-deterministic output.

---

## R1. Audience filter mechanism — DITAVAL via DITA-OT's `--filter` flag

**Decision**: Ship a single `dita/trainee.ditaval` profile alongside the
source tree. The student edition is produced by invoking DITA-OT with
`--filter=<repo>/dita/trainee.ditaval`. The instructor edition is
produced by invoking DITA-OT with no `--filter` argument at all.

The DITAVAL profile contains exactly one rule:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
</val>
```

**Rationale**: DITAVAL is the standard mechanism DITA-OT exposes for
audience-based content filtering. The `--filter` CLI flag has been
stable since DITA-OT 2.x and is documented in the DITA-OT 4.x manual.
Shipping the profile under `dita/` keeps it co-located with the
content it filters, version-controlled with the same diff history,
and reachable from `publish_html.py` via a stable relative path.

**Alternatives considered**:

- *Per-edition source tree fork*. Rejected — directly violates FR-013
  and doubles the surface area for content drift.
- *Custom Python post-processor that strips elements after DITA-OT
  renders them*. Rejected — DITA-OT already does this correctly via
  DITAVAL; reinventing it would be more code, more tests, and more
  risk of leakage. The whole point of `audience` is that DITA-OT
  understands it natively.
- *Use multiple audience values (e.g. `student` and `instructor`)
  rather than the single negated form `-trainee`*. Rejected — the
  existing DITA source (committed by feature 001) already uses
  `audience="-trainee"`. Changing the convention now would force a
  retag of every existing topic; the negated form expresses "for
  everyone *except* trainees" and reads naturally for this feature's
  scope.

---

## R2. Map titles — switch from `title=` attribute to `<title>` child element

**Decision**: Emit the ditamap title as a `<title>` child element of
`<map>` rather than the legacy `title="…"` attribute. The new shape
allows inline `<ph audience="-trainee">` to carry the
"— Instructor Version" decoration.

Before (today, feature 001 shape):

```xml
<map title="Progress Test 1"><topicref href="…"/></map>
```

After (this feature):

```xml
<map>
  <title>Progress Test 1<ph audience="-trainee"> — Instructor Version</ph></title>
  <topicref href="…"/>
</map>
```

For the instructor edition DITA-OT renders the full
`"Progress Test 1 — Instructor Version"` string in the rendered
publication title; for the student edition the trainee filter strips
the `<ph>` element and DITA-OT renders just `"Progress Test 1"`.

**Rationale**: DITA 1.3 added the optional `<title>` element on `<map>`
specifically so map titles can carry inline markup. The `title`
attribute remains a valid fallback when no markup is needed, but it
cannot host child elements and therefore cannot carry an audience-
tagged suffix. DITA-OT honours `<title>` over `title=` when both are
present and emits the same HTML title chrome from either form.

The `<title>` element also unlocks future audience-tagged additions
(e.g. version stamps) without another schema change.

**Alternatives considered**:

- *Keep the `title=` attribute and put "Instructor Version" in a
  separate topic-level intro element*. Rejected — the spec is explicit
  that "Instructor Version" belongs in the document title / page
  header (FR-002c), not in body text. Renderers vary in how they
  surface intro topics in chrome.
- *Use two different `<map>` elements with conditional inclusion at
  filter time*. Rejected — would force two ditamap files per
  publication, doubling the manifest and breaking the "one source
  tree" rule.

---

## R3. Chapter navtitles — switch `<topichead navtitle="…">` to `<topichead><topicmeta><navtitle>…</navtitle></topicmeta></topichead>`

**Decision**: Emit each chapter as `<topichead>` with a child
`<topicmeta>` whose `<navtitle>` element hosts the chapter's display
text, with `<ph audience="-trainee">Instructor </ph>` carrying the
audience-restricted prefix:

```xml
<topichead>
  <topicmeta>
    <navtitle><ph audience="-trainee">Instructor </ph>Week 1 Grams</navtitle>
  </topicmeta>
  <topicref href="main/week-1-grams/gram-01/gram_01.dita"/>
  …
</topichead>
```

For the instructor edition DITA-OT renders the chapter navigation
entry as `"Instructor Week 1 Grams"`; for the student edition the
trainee filter strips the `<ph>` element and the rendered entry reads
`"Week 1 Grams"`.

The chapter folder slug (`week-1-grams/`) is the slugification of
the navtitle's audience-neutral remainder (the text outside the
`<ph audience="-trainee">` element), not the raw chapter string from
the CSV.

**Rationale**: The `navtitle` attribute on `<topichead>` is
attribute-only and cannot carry inline markup, so the audience-tagged
prefix needs a different host. DITA's `<topicmeta>/<navtitle>` element
form is the official replacement and is fully supported by DITA-OT.
This mirrors the R2 decision for map titles — both moves replace
attribute-only metadata with element-form metadata so audience tagging
becomes possible.

Computing the slug from the audience-neutral remainder (rather than
the raw chapter string) is what gives FR-014 its bite: the source
chapter "Instructor Week 1 Grams" produces the slug `week-1-grams`,
which contains no "instructor" substring, satisfying FR-015 for the
student edition (and also producing identical URL paths in both
editions, FR-016).

**Alternatives considered**:

- *Strip the "Instructor " prefix in the extractor (Stage 2) so the
  CSV never carries it*. Rejected — FR-012 forbids changing
  `extract_to_csv.py` or the CSV schema. The normalisation must happen
  inside `generate_dita.py`.
- *Strip the prefix from the slug only, but keep the raw navtitle for
  display in both editions*. Rejected — the spec is clear that the
  word "Instructor" must not appear anywhere in the student edition's
  rendered text (FR-010, FR-015, SC-002).
- *Use `<topichead><title>…</title></topichead>` (the DITA 1.3
  alternative form, parallel to R2)*. Considered and acceptable;
  `<topicmeta>/<navtitle>` was chosen because pub-9 / pub-10 are
  understood to already use this form for chapter metadata, keeping
  the generated DITA aligned with the existing publishing house style.

---

## R4. Chapter-prefix detection — case-insensitive `"Instructor "` only

**Decision**: The generator inspects each chapter string from the CSV
and, if it begins with `"Instructor "` (case-insensitive, exactly one
trailing space), splits it into an audience-restricted prefix
(`"Instructor "`, preserving the source casing) and an audience-neutral
remainder. The remainder is what gets slugified.

Chapters that do not begin with `"Instructor "` flow through
unchanged: the navtitle is emitted as plain text inside `<navtitle>`,
no `<ph>` wrapper, and the slug is the slugified full chapter string.

**Rationale**: Every chapter in the current `source.csv` whose name
contains "Instructor" has it as the leading word followed by a space
(audited via `head source.csv` against the existing CSV). A leading-
substring check is therefore sufficient, and a regex or list-of-
patterns approach would be over-engineering for a corpus this small.
If a future chapter carries "Instructor" mid-string the generator's
behaviour will not strip it; that case can be re-evaluated when (and
if) it arises.

**Alternatives considered**:

- *Strip any occurrence of `"Instructor"` anywhere in the string*.
  Rejected — too aggressive; could mangle hypothetical chapter names
  like "Pre-Instructor Briefing" if such ever appears.
- *Configurable list of audience-restricted prefixes*. Rejected —
  YAGNI; one rule covers every existing case, and the test suite will
  pin the behaviour so a future extension is a small focused change.

---

## R5. Output tree layout — `html/{instructor,student}/{ditamap-stem}/`

**Decision**: DITA-OT's per-ditamap output goes under
`html/instructor/<ditamap-stem>/` and `html/student/<ditamap-stem>/`.
The shared landing page at `html/index.html` links to
`html/instructor/index.html` and `html/student/index.html`; each of
those per-edition index pages lists the publications in that edition
exactly as today's single `html/index.html` does.

Concretely, after a publish run:

```text
html/
├── index.html                       ← NEW: shared landing (two big links)
├── instructor/
│   ├── index.html                   ← per-edition publication list
│   ├── main/                        ← DITA-OT output for main ditamap (instructor)
│   │   └── …
│   ├── progress-test-1/             ← DITA-OT output (instructor)
│   │   └── …
│   └── …
└── student/
    ├── index.html
    ├── main/                        ← DITA-OT output for main ditamap (student)
    │   └── …
    ├── progress-test-1/             ← DITA-OT output (student)
    │   └── …
    └── …
```

URL parity is preserved below the edition segment: any gram reachable
at `html/instructor/main/week-1-grams/gram-01/gram_01.html` is also
reachable at `html/student/main/week-1-grams/gram-01/gram_01.html`
with the audience-tagged content stripped (FR-016).

**Rationale**: This is the simplest layout that satisfies FR-005
(distinct, clearly-named locations), FR-006 (single top-level landing
page), FR-007 (per-edition publication index), and FR-016 (URL
parity). DITA-OT's `--output=` flag accepts any path, so directing it
once at `html/instructor/<stem>/` and once at `html/student/<stem>/`
is a two-line change.

**Alternatives considered**:

- *Single tree with audience-aware index pages that show different
  content based on a query string*. Rejected — requires JavaScript at
  view time, contradicts the static-HTML constraint, and breaks the
  "no `instructor` substring under `student/`" guarantee.
- *Suffix-based naming (`html/main-instructor/`,
  `html/main-student/`)*. Rejected — flattens two orthogonal
  dimensions (publication × edition) into one and makes the per-
  edition index harder to write.

---

## R6. Shared landing page — minimal static HTML, no JS

**Decision**: `html/index.html` is generated by `publish_html.py` as
a static HTML page with two prominent links (instructor edition,
student edition), each labelled with a one-sentence description of
the audience. It carries a generation timestamp in the same format
as today's `write_root_index()` output for parity with feature 002's
landing page.

The page is byte-deterministic (FR-008): the timestamp is sourced from
the `SOURCE_DATE_EPOCH` environment variable when set (standard
reproducible-build convention), falling back to a fixed string when
not. Two consecutive publish runs from the same checkout produce
byte-identical `html/index.html`.

**Rationale**: The landing page's job is to disambiguate the two
editions in one click (SC-004). No JavaScript, no styling beyond the
project's existing baseline, no audience-detection logic — a reviewer
chooses with one click. Reproducibility matches the existing
publish_html.py contract.

**Alternatives considered**:

- *Redirect `html/index.html` to one edition (e.g. always student)*.
  Rejected — fails SC-004 (one click to either edition) and risks
  trapping instructors at the student page if they bookmark `html/`.
- *Render edition names with embedded styling / illustrations*.
  Rejected — overkill for the current corpus; the existing minimal
  HTML style is well understood by the team.

---

## R7. Idempotency under DITA-OT — strip the generation timestamp from rendered HTML

**Decision**: DITA-OT 4.x emits a `<meta name="DC.date.created" …>`
header (and sometimes a generated comment) into every rendered HTML
page that carries the build wall-clock time. The publisher's existing
`prettify_tree()` pass already walks every emitted HTML file; the
prettifier will be extended to **also** remove (or stamp to a fixed
value) any DC.date.created meta and any DITA-OT generation comment,
so two consecutive runs over an unchanged DITA source produce
byte-identical HTML in both editions.

The dual-edition build run is treated as one logical run for the
purposes of FR-008: both editions are emitted by the same invocation
and both must round-trip byte-identically on a second invocation
against unchanged input.

**Rationale**: Feature 001 set FR-013 / SC-004 (idempotent generator
output) for the DITA tree; this feature extends the same guarantee to
the published HTML tree (SC-006). DITA-OT's wall-clock metadata is
the only known non-deterministic field in its HTML5 output, and the
prettifier is already the post-processing seam in `publish_html.py`.

**Alternatives considered**:

- *Set `SOURCE_DATE_EPOCH` and trust DITA-OT to honour it*. Rejected —
  DITA-OT 4.x does not consistently honour `SOURCE_DATE_EPOCH` across
  all formats; a hash-comparison test would still occasionally fail.
  Stripping/stamping in the prettifier is local, testable, and
  doesn't depend on toolchain behaviour we can't pin.
- *Skip idempotency for the HTML tree and only assert it for `dita/`*.
  Rejected — SC-006 explicitly extends the idempotency contract to
  HTML output.

---

## R8. Backwards compatibility — pre-existing `html/<publication>/` deep links

**Decision**: After this feature ships, `html/<publication>/…` URLs
that worked before this change (today: `html/main/…`,
`html/progress-test-1/…`) will not resolve. The new shared
`html/index.html` is the authoritative entry point; existing
consumers are pointed at it and re-derive their bookmarks from the
edition-segment-aware paths. No redirect shim, no 404 page with
hints.

**Rationale**: Feature 002's PR-preview workflow consumes the
landing page, not deep links into specific publications, so the
visible breakage on the CI surface is the landing page swap. Internal
team bookmarks are few and easily updated.

The spec's edge case for pre-existing deep links offers three
behaviours (redirect / 404-with-hint / remain-valid pointing to one
edition); we choose plain failure (paths simply don't exist) as the
simplest behaviour, on the explicit understanding that the new
landing page covers re-discovery.

**Alternatives considered**:

- *Emit a top-level `redirect.html` for each old publication path*.
  Rejected — implies static-server redirect support that GitHub
  Pages provides only via meta-refresh tricks, which conflict with
  the no-JS landing-page decision.
- *Default `html/<publication>/` to the student edition*. Rejected —
  silently sends old bookmarks to a filtered view, which is exactly
  the leakage shape this feature exists to prevent (in reverse).

---

## R9. Testing strategy — extend two test modules, no new modules

**Decision**:

- `tests/test_generate_dita.py` gains assertions for:
  - Chapter slug normalisation (CSV chapter `"Instructor Week 1 Grams"`
    → folder slug `week-1-grams`, no `instructor-` prefix anywhere in
    the source tree).
  - Chapter navtitle decomposition (the emitted ditamap contains
    `<navtitle><ph audience="-trainee">Instructor </ph>Week 1 Grams</navtitle>`).
  - Map-title decomposition (the emitted ditamap contains
    `<title>Progress Test 1<ph audience="-trainee"> — Instructor Version</ph></title>`
    and **does not** carry a legacy `title=` attribute on `<map>`).
- `tests/test_publish_html.py` gains assertions for:
  - Two parallel output trees (`html/instructor/`, `html/student/`)
    exist after a publish run, each with its own `index.html`.
  - The shared `html/index.html` exists and links to both per-edition
    indexes.
  - A full-text grep for the case-insensitive substring `"instructor"`
    over every file *and every path component* under `html/student/`
    returns zero matches (SC-002).
  - Sample-gram URL parity: for at least one gram known to carry both
    a vessel name and an analysis sheet, the file at
    `html/instructor/<…>/gram_NN.html` exists, the file at
    `html/student/<…>/gram_NN.html` exists, and the latter contains
    neither the vessel-name text nor an analysis-sheet section
    (SC-001, SC-003).
  - Idempotency: two consecutive publish runs against the same DITA
    source produce byte-identical files under `html/` (SC-006).

No new test modules. The fixture tree (`tests/fixtures/`) gains one
small DITA fixture exercising both the navtitle decomposition and the
map-title decomposition, mirroring the style of the existing fixtures.

**Rationale**: The two affected scripts already have paired test
modules; extending those modules keeps the test suite's structure
flat and matches the project convention.

**Alternatives considered**:

- *Add a new `test_audience_filter.py` module for the new behaviour*.
  Rejected — splits the testing of `generate_dita.py` and
  `publish_html.py` across more files than necessary; the existing
  per-script modules are the right home.

---

## R10. DITAVAL profile filename and location

**Decision**: `dita/trainee.ditaval`, committed alongside the rest of
the DITA source tree. `publish_html.py` references it by a stable
relative path derived from its `--dita` argument (`<dita>/trainee.ditaval`).
If the file is missing the publisher logs a clear error and exits
non-zero — the dual-edition shape is the only supported mode.

**Rationale**: Co-locating the profile with the content it filters
keeps the diff history aligned. Naming the file after the audience it
excludes (`trainee.ditaval`) leaves room for future profiles
(`reviewer.ditaval`, etc.) without renaming.

**Alternatives considered**:

- *Embed the DITAVAL XML inside `publish_html.py` as a string
  constant and write it to a temporary file at publish time*.
  Rejected — hides a content-shaped artefact in code, can't be
  version-controlled or diffed cleanly, and an air-gapped maintainer
  would have to read Python to know what's filtered.
- *Ship the profile under `specs/003-…/`*. Rejected — the profile is
  a runtime input to the publisher, not a spec document.

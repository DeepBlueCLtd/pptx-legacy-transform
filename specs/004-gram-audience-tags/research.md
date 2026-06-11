# Phase 0 Research: Per-Gram Audience Tags via CSV `audience` Column

**Feature**: Per-Gram Audience Tags via CSV `audience` Column
**Date**: 2026-05-22

This document records the decisions taken to resolve the technical
unknowns the spec left implicit, and the best-practice choices for
each DITA / DITA-OT / CSV mechanism the feature depends on. The
feature must keep idempotency parity with features 001 / 003
(FR-014 / SC-004) and add only one column to the CSV contract, so
several decisions trade flexibility for stable, forward-compatible
output.

---

## R1. PPTX → CSV: trailing `[xxx]` syntax and parsing rule

**Decision**: The extractor (`extract_to_csv.py`, function
`_split_descriptor`) gains a regex pass that, on the right-hand side
of the `Gram N:` colon, repeatedly consumes any trailing bracketed
group `[ … ]` and records the inside text. The bracketed group is
allowed to be preceded by optional whitespace. The captured inside
strings are joined with a single space and written into the new
`audience` column for every CSV row produced from that gram. The
remaining (audience-stripped) text is what becomes `vessel_name`.

Concretely, the right-hand side of a descriptor matches this pattern
(applied right-to-left, repeatedly, until no trailing bracketed
group remains):

```regex
^(?P<head>.*?)\s*\[(?P<tag>[^\[\]]+)\]\s*$
```

After the loop:

- `head` is what becomes the new `vessel_name` value (trimmed).
- The captured `tag` values are joined with a single space (in
  source order — i.e. the order they appeared left-to-right in the
  PPTX descriptor) and written to the `audience` cell on every row
  the gram emits.

**Examples**:

| PPTX descriptor (right of colon) | `vessel_name` | `audience` cell |
|---|---|---|
| `FR Vessel, Category 1, Bespin` | `FR Vessel, Category 1, Bespin` | (empty) |
| `FR Vessel, Category 1, Bespin [-own]` | `FR Vessel, Category 1, Bespin` | `-own` |
| `FR Vessel, Category 1, Bespin [-other]` | `FR Vessel, Category 1, Bespin` | `-other` |
| `FR Vessel, Category 1, Bespin [-own][-other]` | `FR Vessel, Category 1, Bespin` | `-own -other` |
| `FR Vessel, Category 1, Bespin [-own] [-other]` | `FR Vessel, Category 1, Bespin` | `-own -other` |
| `[-other]` | (empty) | `-other` |

**Rationale**: This puts the audience tag in the *one* PPTX location
where the author already encodes per-gram metadata: the descriptor
text after the colon. The bracket syntax is unambiguous against
real-corpus descriptors (a square-bracket suffix has never been seen
in feature 001's vessel-name corpus per the existing tests), and a
greedy right-side strip is the simplest reversible mapping that
survives both the `[-own][-other]` and `[-own] [-other]` authoring
styles the user already chose to commit. Stripping from the right
means a vessel name that legitimately contains brackets in its
middle (none today, but conceivable) is unaffected — only the
trailing brackets travel into `audience`.

**Alternatives considered**:

- *Encode tags inside `gram_id` (left of colon)*. Rejected — would
  break feature 001's csv-schema.md §3 invariant that `gram_id` is a
  plain integer string. The whole point of `gram_id`'s shape is
  cheap refactoring (renumber a gram by typing a new integer in the
  cell); piggy-backing audience tags on it would force the author
  to reason about two concerns in one cell.
- *Use a non-bracket sigil (e.g. `@-own`, `#-other`)*. Rejected —
  brackets read naturally as a parenthetical aside, are visually
  distinct in PowerPoint, and the user already committed Week 3 PPTX
  changes using the `[…]` form.
- *Require a single bracket group with space-separated inside text
  (`[-own -other]`)*. Rejected — the user explicitly chose
  `[-own][-other]` / `[-own] [-other]` in the Week 3 edits, so the
  parser must accept multiple adjacent groups. We accept both forms
  and canonicalise to space-separated in the CSV.

---

## R2. CSV column placement and forward compatibility

**Decision**: Append a 17th column named `audience` to the right of
the existing `warnings` column. Update
`specs/001-pptx-dita-migration/contracts/csv-schema.md` to document
the new column (and, in the same edit pass, drop the stale
`analysis_docx_path` row that has never matched the actual extractor
output — it was carried in the contract from an earlier design pass
but never wired into `CSV_COLUMNS` in `extract_to_csv.py`). The
generator's CSV reader treats a missing 17th column (a legacy
16-column CSV) as if every row had an empty 17th cell.

**Rationale**: Appending at the right edge is the minimum-impact
change to the column order. Older CSVs (e.g. a hand-edited copy
predating this feature) round-trip cleanly: read as 16 columns,
write as 17 with empty audience cells. No flag-day migration, no
versioning column. The `analysis_docx_path` cleanup is in-scope here
because the new column's documented position only makes sense once
the stale row is removed — otherwise the doc would claim `audience`
sits at position 18 when the on-disk column count says 17 (16 real
columns + audience).

The DictReader/DictWriter pair already in use by the extractor and
generator handles missing trailing keys gracefully when fed an
`extrasaction='ignore'` writer and a tolerant reader (the reader
returns `None` for missing keys, which we normalise to `""` before
emitting on the topicref).

**Alternatives considered**:

- *Insert the new column adjacent to `vessel_name` (a semantic
  neighbour)*. Rejected — would shift the column-index of every
  downstream column, breaking any pinned column-order reader (e.g.
  manual `csv.reader` consumers).
- *Bump a CSV schema-version row at the top of the file*. Rejected
  — over-engineering; the CSV is consumed by exactly one Python
  pair (`extract_to_csv.py` writer / `generate_dita.py` reader) and
  one human review pass, all of which can be taught the
  forward-compat rule in one place.

---

## R3. DITA emission site: topicref attribute, not topic root

**Decision**: The DITA generator emits the per-gram `audience` value
as an `audience="…"` attribute on the `<topicref>` element in each
ditamap. The gram's `<topic>` element (and its root `<topic>` file)
carries no `audience` attribute attributable to this feature.

**Rationale**: The spec is explicit (FR-005, FR-006): the audience
attribute lives on the topicref so that the *index page* hides the
gram for the excluded audience. The topic file itself stays
audience-neutral — a reader who reaches it via a direct URL (e.g. a
bookmark, an external link, or a search index) sees the unfiltered
topic, because the audience filter only acted on the link in the
parent ditamap.

This matches DITA-OT's semantics: an excluded `<topicref>` causes
DITA-OT to (a) omit the corresponding link from the rendered
navigation/index, and (b) skip emission of the topic's HTML file
under that build's output tree. The topic *file in the DITA source*
is unchanged, and a parallel build with a different filter will emit
the same topic where its topicref is included.

**Alternatives considered**:

- *Tag the topic root element (`<topic audience="…">`) instead*.
  Rejected — would cause DITA-OT to also strip nested content if the
  audience matched any inner element's filter, and would mean the
  topic file is invisible to any reader regardless of how they
  arrived. The user's requirement is explicitly index-level
  filtering, not topic-level.
- *Tag both the topic root and the topicref*. Rejected — redundant
  and would double the test surface.

---

## R4. Per-gram consistency: fail-fast in the generator, not the extractor

**Decision**: The extractor writes the same `audience` value to
every CSV row produced from one gram (it has the parsed value in
hand at the point it emits all the gram's rows). The generator, on
the read side, asserts consistency across the rows of one
`(publication, chapter, gram_id)` group and raises a clear,
gram-named exception on mismatch. The exception message identifies
the publication, chapter, and gram_id of the inconsistent group, and
lists the conflicting values.

**Rationale**: Two failure-mode separations matter here:

1. *Authoring error* (someone hand-edited one row's audience cell
   but not the gram's other rows) → caught at DITA-generate time
   with a clear name. The author re-opens the CSV and fixes it.
2. *Programmatic error* (the extractor's regex is buggy and emits
   different values per row) → caught at the same point, named the
   same way, surfaces during development.

The extractor cannot meaningfully detect (1) because by definition
it computes the value once per gram. The generator is the right seam
because it groups rows by gram (it already does for `topic_filename`
sharing) and so is naturally positioned to assert that the values
agree across the group.

**Alternatives considered**:

- *Validate during a separate CSV-lint pass before the generator
  runs*. Rejected — adds a new top-level script for no benefit; the
  generator already has the gram-grouping pass.
- *Silently take the first row's value and warn about the
  inconsistency*. Rejected — the spec calls for fail-fast (SC-007),
  and silent disagreement reads to the author as "audience filtering
  is mysteriously broken on this gram."

---

## R5. DITAVAL profile composition for the three editions

**Decision**: The DITA generator emits three DITAVAL profiles into
its output directory (next to the ditamaps) — none are committed
source files. The function `generate_dita.write_trainee_ditaval` is
renamed to `write_ditaval_profiles` and writes all three files in
one pass:

- `trainee.ditaval` — excludes `audience='trainee'`. Unchanged in
  shape from feature 003, but now emitted as one of three siblings
  rather than the sole DITAVAL file. Kept in place so the feature-
  003 contract still resolves on read; the publisher does not
  reference it directly in this feature (the trainee rule is
  composed into the two student profiles).
- `student-own.ditaval` (NEW) — excludes `audience='trainee'` *and*
  `audience='own'`. Used to render `html/student-own/`.
- `student-other.ditaval` (NEW) — excludes `audience='trainee'`
  *and* `audience='other'`. Used to render `html/student-other/`.

Each new file is two `<prop>` lines:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<val>
  <prop att="audience" val="trainee" action="exclude"/>
  <prop att="audience" val="own" action="exclude"/>
</val>
```

(and the equivalent for `student-other`).

**Rationale**: DITAVAL composes by listing multiple `<prop>` rules
inside one `<val>`; DITA-OT applies each rule independently. Two
files (one per nation) is the minimum that lets the publisher emit
two distinct student trees in one invocation per ditamap.

The audience values stored in DITA are `-trainee`, `-own`,
`-other` (with the leading hyphen, per feature 003's convention).
The DITAVAL rule's `val=` attribute is just the bare token without
the leading hyphen — DITA-OT's filter logic interprets the leading
hyphen in the DITA attribute as "this element is excluded *from*
the matching audience" (negative form). So the profile filename
(`student-own.ditaval`) matches the audience it gates against,
without the negation sign.

**Alternatives considered**:

- *Commit the DITAVAL files under `dita/` as source artefacts*.
  Rejected — feature 003 already established that `trainee.ditaval`
  is generator-emitted (see `generate_dita.write_trainee_ditaval`),
  and committing the two new profiles would split the DITAVAL
  population across two sources (one generated, two committed) for
  no benefit. Generating all three from one function in the
  generator keeps the audience contract single-sourced.
- *One DITAVAL file with all three rules and per-edition `<revprop>`
  filtering*. Rejected — DITA-OT's `--filter` flag takes one file
  per build; we'd still need to emit three profiles or run three
  builds with different rev selectors. Three small files is the
  cleaner shape.
- *Combine the two student profiles via DITAVAL include of
  `trainee.ditaval`*. The DITAVAL schema technically supports
  `<style-conflict-behavior>` but not include directives — there is
  no portable way to compose two files at filter time. Inlining the
  trainee rule into each student profile is the supported approach.

---

## R6. Output tree layout: instructor + student-own + student-other

**Decision**: After this feature ships, the `html/` tree carries
three top-level subdirectories:

```text
html/
├── index.html                       # shared landing (three big links)
├── instructor/                      # unfiltered (unchanged from feature 003)
│   └── …
├── student-own/                     # NEW — excludes -trainee + -own
│   └── …
└── student-other/                   # NEW — excludes -trainee + -other
    └── …
```

The single `html/student/` subtree feature 003 produced is removed;
its contents are not migrated (re-derived by the publish run instead).

**Rationale**: Three nation-specific subtrees is the minimum that
delivers the spec's User Story 1 — both student-nation users must
reach an audience-appropriate index from the shared landing page in
one click. URL parity within each student edition is preserved
exactly as feature 003's R5 specified (URL paths below the
edition-segment root match the instructor edition for every gram
that survives the filter).

**Alternatives considered**:

- *Keep `html/student/` as a third edition (the union of `-own`
  and `-other` exclusions, i.e. only "shareable to all students")*.
  Rejected — a four-edition layout exceeds the spec's three-edition
  contract (FR-007 / FR-008) and confuses the landing page.
- *Suffix-based naming under `student/` (e.g. `html/student/own/`,
  `html/student/other/`)*. Considered — keeps the "student" segment
  visible. Rejected because feature 003's URL-parity rule attaches
  to the top-level edition segment, and a two-level student path
  would break URL substitution (`instructor/main/…` ↔
  `student/own/main/…` is not a single-segment swap). Flat
  `student-own/` and `student-other/` preserve single-segment swap.
- *Drop the instructor edition*. Rejected — the instructor still
  needs the unfiltered view for course-author review, per feature
  003's User Story 2.

---

## R7. Mock corpus generator: where to plant the audience tags

**Decision**: The mock corpus generator (`mock_pptx.py`) plants
`[-own]` and `[-other]` tags on the *last two grams of the second
grams slide* of `Instructor Week 3 Grams`, mirroring the real-corpus
edit the user has just committed in the actual PPTX. The choice is
deterministic for a fixed RNG seed.

The `Instructor Progress Test 3 Grams No FR` `Publication` entry is
removed from the `PUBLICATIONS` tuple. The `no_fr` field on the
`Publication` dataclass and the `"FR "` prefix logic inside
`_pick_descriptor` are *retained* (they are orthogonal authoring
affordances — the field controls a vessel-prefix style decision, not
an audience decision) but no publication instantiates them.

**Rationale**: Mock-corpus determinism (carried over from feature
001) means the test suite can pin the exact two grams that get
`[-own]` / `[-other]` markers and assert against them. The Week 3
choice mirrors what the user has actually done in the real PPTX,
which is the single source of truth for the manual edit; replicating
that shape in the mock keeps the end-to-end pipeline exercised
end-to-end.

Retaining `no_fr` but not instantiating it preserves the option to
re-add a no-FR variant in the future without re-introducing the
removed code; this is a low-cost choice.

**Alternatives considered**:

- *Plant tags on a representative gram of every publication*.
  Rejected — over-instruments the mock corpus and makes the
  assertions noisier (we'd be testing the tag plumbing on
  publications the user has not actually tagged in real life).
- *Delete the `no_fr` field and `"FR "` prefix logic entirely*.
  Rejected — the prefix style is an authoring affordance, not a
  feature; deleting it would over-prune the mock generator and
  potentially regress tests that pin vessel-descriptor variety.

---

## R8. Unknown-token tolerance and logging

**Decision**: The DITA generator emits whatever audience tokens
appear in the CSV cell, verbatim (after whitespace normalisation),
on the topicref. It maintains an internal allow-list of *recognised*
tokens (`-trainee`, `-own`, `-other`) — purely for logging purposes.
When a CSV cell contains a token outside the allow-list, the
generator logs a `WARNING` line naming the gram, the token, and the
allow-list. The build proceeds normally; DITA-OT silently ignores
audience tokens that no DITAVAL profile mentions, so an unknown
token is a no-op in publication.

The generator's allow-list is hard-coded (not configurable) — its
sole job is to surface authoring typos. A future feature adding a
fourth audience would extend the constant in one place.

**Rationale**: The user's intent is for the `audience` column to be
a human-editable cell — typos are inevitable. A silent fall-through
(today's behaviour with an empty allow-list) means a typo like
`-orher` silently shows the gram in every edition, which the author
then has to discover by spot-checking. A warning-level log surfaces
the typo without breaking the build (which would block a
production publish on a typo).

Include-style tokens (no leading hyphen) are a separate case: they
are flagged as an authoring error and the build fails (FR-016 +
edge-case bullet on non-exclude tokens). This is because an
include-style token would either match nothing (silent broken
filter) or unexpectedly *include* an element only when a particular
audience is selected, which is the opposite of this feature's
contract.

**Alternatives considered**:

- *Fail the build on any unknown token*. Rejected — would block
  publishing on an authoring typo that has no production impact (the
  unknown token is a no-op). A WARNING line is the right severity.
- *Drop the allow-list entirely*. Rejected — would mean typos
  publish silently with no observable signal.

---

## R9. Idempotency under the dual-student build

**Decision**: The dual-student build extends feature 003's
idempotency guarantee (FR-008 / SC-006) to the third edition without
modification. The publisher's existing `prettify_tree()` pass
(extended by feature 003's R7 to strip the DITA-OT-generated
timestamp) runs over each of the three edition subtrees and
produces byte-identical output on a second invocation.

The shared `html/index.html` continues to derive its timestamp from
`SOURCE_DATE_EPOCH` (or fall back to a fixed string, per feature
003's R6).

**Rationale**: Feature 003's R7/R6 decisions were chosen specifically
to extend cleanly to more editions; nothing in those decisions was
two-edition-specific. Adding a third edition is a configuration
change in the publisher, not a new approach to determinism.

**Alternatives considered**:

- *Re-validate idempotency from scratch for the third edition*.
  Not really an alternative — we still do the same byte-comparison
  test, just over three subtrees instead of two.

---

## R10. CSV reader/writer forward-compat path

**Decision**: The generator's CSV reader (`csv.DictReader`)
normalises each row's `audience` value via:

```python
audience = (row.get("audience") or "").strip()
audience = " ".join(audience.split())   # normalise internal whitespace
```

A row with no `audience` key (legacy 16-column CSV) yields `""`.
The extractor's CSV writer (`csv.DictWriter`) emits the 17th column
header on every produced CSV; the value on each row is the
parsed-and-normalised audience string (or `""` if no tag was
present in the descriptor).

The `CSV_COLUMNS` constant at the top of `extract_to_csv.py`
(today: 16 entries, after main's `file_size` addition) gains
`"audience"` as its 17th entry, and the generator's column-count
check is updated to accept both 16- and 17-column CSVs (a 16-column
CSV is treated as having an implicit empty 17th column).

**Rationale**: The whitespace normalisation handles the human-edit
edge case (the spec explicitly calls out that re-runs over a
human-edited CSV must be byte-identical to re-runs over a freshly-
extracted CSV). The dual-column-count tolerance is the forward-compat
lever — older CSVs round-trip without manual migration.

**Alternatives considered**:

- *Require all CSVs to have 17 columns and emit a migration tool*.
  Rejected — over-engineering for a one-column change. The Python
  CSV libraries already handle missing trailing keys gracefully.
- *Use a non-DictReader column-position reader and pin column 17
  explicitly*. Rejected — DictReader is what the existing code uses;
  a position-pinned reader would be inconsistent with the rest of
  the pipeline.

---

## R11. Testing strategy — extend four existing test modules + two web tests

**Decision**:

- `tests/test_extract_to_csv.py` gains assertions for:
  - The new `audience` column is emitted in every produced CSV
    header (17 columns).
  - A descriptor of the form `"Gram 7: FR Vessel [-own]"` produces
    `vessel_name="FR Vessel"` and `audience="-own"` on every row of
    gram 7.
  - A descriptor with two adjacent bracketed groups
    (`[-own][-other]` and `[-own] [-other]`) produces
    `audience="-own -other"`.
  - A descriptor with no bracketed group produces an empty
    `audience` cell.

- `tests/test_generate_dita.py` gains assertions for:
  - A row with `audience="-other"` produces an `audience="-other"`
    attribute on the matching topicref inside the per-publication
    ditamap.
  - A row with empty `audience` produces a topicref with **no**
    `audience` attribute (not `audience=""`).
  - Two CSV rows of the same gram with conflicting `audience` values
    raise a named exception (the exception message mentions the
    publication, chapter, and gram_id).
  - The generator accepts a 16-column legacy CSV (no audience
    column) and emits topicrefs with no audience attribute on any.
  - An unknown audience token (e.g. `-foo`) is emitted verbatim and
    a WARNING is logged.
  - `write_ditaval_profiles` writes three files
    (`trainee.ditaval`, `student-own.ditaval`, `student-other.ditaval`)
    to the output directory and each has the expected `<prop>` rules
    (see R5).

- `tests/test_publish_html.py` gains assertions for:
  - After a publish run, the directories
    `html/instructor/`, `html/student-own/`, `html/student-other/`
    exist; `html/student/` does NOT.
  - The shared `html/index.html` links to all three per-edition
    indexes.
  - In each student-own progress-test index page, the number of
    `<a>` links to gram pages equals the number in the corresponding
    student-other page (Week 3 substitution: `-own` gram is hidden
    from student-own, `-other` gram is hidden from student-other,
    same count).
  - A full-text grep over `html/` for the case-insensitive substring
    `"no fr"` returns zero matches.
  - Idempotency: two consecutive publish runs against the same DITA
    source produce byte-identical files under `html/` across all
    three editions.
  - The publisher refuses to build if any of the three required
    DITAVAL profiles is missing from the staging tree (a previously-
    trainee-only check, now generalised over the trio).

- `tests/test_mock_pptx.py` changes:
  - Delete `test_no_fr_variant_drops_fr_prefix` — its target
    publication (`Instructor Progress Test 3 Grams No FR`) is
    removed from `PUBLICATIONS` in this feature. The `no_fr` field
    and the `"FR "` prefix logic remain in `mock_pptx.py` (per R7)
    so future re-introduction is cheap, but the test currently
    relies on a publication that does not exist.
  - Add `test_week_3_carries_audience_markers`: build the mock
    Week 3 PPTX with the fixed seed, parse its second grams slide,
    assert the second-to-last gram's descriptor ends with `[-other]`
    and the last gram's descriptor ends with `[-own]`.

- `tests/web/student-edition.test.js` is REWRITTEN: the existing
  single-edition block becomes two describe-blocks, one per nation:
  - `describe("student-own edition", …)` — load
    `html/student-own/progress-test-3/index.html`, assert the
    `-own`-tagged gram is absent from the index links, assert the
    `-other`-tagged gram is present.
  - `describe("student-other edition", …)` — load
    `html/student-other/progress-test-3/index.html`, symmetric
    assertions.

- `tests/web/instructor-edition.test.js` URL-parity test:
  - Replace the single `for each surviving student path, assert
    instructor has the same path` check with two passes (one for
    each student edition).
  - The instructor edition continues to assert it sees every gram
    (the union of surviving paths across both student editions).

No new Python test modules. No new fixture corpus — the existing
mock corpus (with the changes from R7) is the fixture.

**Rationale**: Each affected script already has a paired test
module; extending those keeps the test suite's flat structure and
matches the convention features 001 / 002 / 003 established. The
web-test rewrite is mechanical (the existing
`student-edition.test.js` and `instructor-edition.test.js` files
both target a single student edition that no longer exists — they
must be reshaped to match the new three-edition layout regardless
of how the assertions evolve).

**Alternatives considered**:

- *Add a new `test_audience_column.py`*. Rejected — splits per-
  feature concerns across files in a way the existing module layout
  does not.
- *Keep `tests/web/student-edition.test.js` as a single block that
  iterates over the two student editions*. Rejected — the loop
  obscures which assertions are nation-specific versus shared, and
  the per-edition describe-blocks read more naturally in the
  Jest/Vitest output.

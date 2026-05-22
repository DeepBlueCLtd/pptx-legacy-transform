# Contract: Three-Edition HTML Output Tree

**Feature**: Per-Gram Audience Tags via CSV `audience` Column
**Status**: Draft (replaces feature 003's two-edition layout)

This contract defines the shape of the `html/` output tree after
this feature ships and the responsibilities of the shared landing
page.

## 1. Top-level tree

```text
html/
├── index.html              # shared landing page (three big links)
├── instructor/             # unchanged from feature 003
│   ├── index.html          # per-edition publication index
│   ├── main/
│   │   └── …
│   ├── progress-test-1/
│   │   └── …
│   ├── progress-test-2/
│   │   └── …
│   ├── progress-test-3/
│   │   └── …
│   ├── progress-test-4/
│   │   └── …
│   ├── progress-test-5/
│   │   └── …
│   ├── progress-final-assessment/
│   │   └── …
│   └── pub10-ed22b-updated/
│       └── …
├── student-own/            # NEW (replaces feature 003's html/student/)
│   ├── index.html
│   ├── main/
│   │   └── …
│   ├── progress-test-1/
│   │   └── …
│   ├── progress-test-2/
│   │   └── …
│   ├── progress-test-3/    # the substitution case (no -own grams)
│   │   └── …
│   ├── progress-test-4/
│   │   └── …
│   ├── progress-test-5/
│   │   └── …
│   ├── progress-final-assessment/
│   │   └── …
│   └── pub10-ed22b-updated/
│       └── …
└── student-other/          # NEW
    ├── index.html
    ├── main/
    │   └── …
    └── (same publication subtree as student-own; differs in -other vs -own exclusion)
```

The single `html/student/` subtree that feature 003 produced is
removed entirely. The publisher is responsible for cleaning the
output tree before each run so a stale `html/student/` does not
linger across the upgrade.

## 2. Edition naming

| Subdir | Audience | DITAVAL filter |
|---|---|---|
| `instructor/` | instructors and authors | none (unfiltered) |
| `student-own/` | students of the "own" nation | excludes `-trainee` and `-own` |
| `student-other/` | students of the "other" nation | excludes `-trainee` and `-other` |

The two student subdir names are chosen as flat, hyphen-separated
slugs so URL substitution between editions remains a single-segment
swap (e.g.
`html/student-own/progress-test-3/gram-08/gram_08.html` ↔
`html/student-other/progress-test-3/gram-08/gram_08.html`).

## 3. Shared landing page (`html/index.html`)

### 3.1 Structure

The page lists three editions in a fixed order:

1. **Instructor edition** (unfiltered)
2. **Student edition — own nation** (excludes own-nation-restricted grams)
3. **Student edition — other nation** (excludes other-nation-restricted grams)

Each entry carries a one-sentence audience description so a reviewer
at the landing page can tell the three apart without clicking
through. The link order is hard-coded in the publisher; the page is
byte-deterministic.

### 3.2 Determinism

The page carries a single generation timestamp sourced from
`SOURCE_DATE_EPOCH` (or a fixed fallback string), per feature 003
R6. No JavaScript, no audience-detection logic, no per-visitor
content variation.

### 3.3 Example shape

(Implementation may differ in styling; the contract is the
structural shape.)

```html
<!DOCTYPE html>
<html>
<head><title>Legacy Transform — Editions</title></head>
<body>
  <h1>Legacy Transform — Editions</h1>
  <ul>
    <li>
      <a href="instructor/index.html">Instructor edition</a> —
      unfiltered; every gram visible, instructor-only content
      (vessel names, analysis sheets) shown.
    </li>
    <li>
      <a href="student-own/index.html">Student edition — own nation</a> —
      excludes instructor-only content and any gram classified
      for the own nation.
    </li>
    <li>
      <a href="student-other/index.html">Student edition — other nation</a> —
      excludes instructor-only content and any gram classified
      for the other nation.
    </li>
  </ul>
  <p><small>Generated &lt;timestamp&gt;</small></p>
</body>
</html>
```

## 4. Per-edition index

Each per-edition subdir carries an `index.html` listing the
publications in that edition exactly as feature 003 specified. The
shape is unchanged; only the audience filter applied to each
publication's content differs.

## 5. URL parity

For any path P under one student edition's subtree, the same path
under the other student edition's subtree either:

- Exists and refers to the same gram with the same filter applied
  (the gram is not audience-restricted for either nation), or
- Does not exist in exactly one of the two trees (the gram is
  audience-restricted for that nation).

A path that exists in BOTH student trees AND in the instructor tree
refers to the same gram; the rendered content in each tree differs
only by the audience filter applied to the inner content (i.e. the
`-trainee` filter on vessel-name and analysis-sheet content; the
`-own` / `-other` topicref filter only ever causes whole-page
absence, never partial filtering of inner content).

A path that exists in the instructor tree but in NEITHER student
tree corresponds to a gram tagged with both `-own` and `-other`.

## 6. Substitution semantics (Week 3 case)

When the CSV pairs each `-own`-tagged gram with an `-other`-tagged
sibling gram within the same publication+chapter:

- The total number of grams listed on the `student-own` edition's
  index page for that publication+chapter equals the total number
  of grams listed on the `student-other` edition's index page.
- Each edition's listing differs from the other by exactly two
  grams: one tagged `-own` (absent from student-own, present in
  student-other) and one tagged `-other` (present in student-own,
  absent from student-other).

When the pairing is not balanced (e.g. an author tags one gram
`-other` without a matching `-own` substitute), the counts naturally
differ — this is a reportable property of the authored content, not
a publish bug.

## 7. Backward compatibility

Pre-feature-004 deep links into `html/student/...` paths return 404
after the upgrade. The new shared landing page is the authoritative
entry point; existing consumers re-derive their bookmarks. No
redirect shim is emitted.

This matches feature 003's treatment of pre-existing
`html/<publication>/...` deep links (R8 of feature 003 research):
the breakage surface is the landing page swap, not silent
mis-routing.

## 8. Cleanup before each publish

The publisher's existing pre-run cleanup step (carried over from
feature 003) removes stale top-level subdirs under `html/`. After
this feature, the cleanup step removes `html/student/` along with
the other stale roots so an upgraded checkout does not retain a
mixed two-edition + three-edition layout.

The cleanup is conservative: it removes only known-stale top-level
subdirs by exact name, never `*` glob delete. Adding the
`student/` name to the cleanup list is a one-line change.

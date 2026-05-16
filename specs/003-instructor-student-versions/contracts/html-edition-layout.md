# Contract: HTML Edition Layout

This document fixes the exact directory shape under `html/` after a
publish run, the contract of the shared landing page, and the
contract of each per-edition publication index.

It is the authoritative reference for the test assertions in
`tests/test_publish_html.py` that cover SC-004, FR-005, FR-006,
FR-007, and FR-016.

## 1. Directory tree

After a successful `publish_html.py` run:

```text
html/
├── index.html                       ← shared landing (§2)
├── instructor/                      ← FR-005 distinct location
│   ├── index.html                   ← per-edition publication index (§3)
│   ├── main/                        ← DITA-OT output for main.ditamap
│   │   ├── index.html
│   │   ├── main/                    ← DITA-OT preserves the in-map href tree
│   │   │   └── week-1-grams/
│   │   │       └── gram-NN/
│   │   │           └── gram_NN.html
│   │   └── …
│   ├── progress-test-1/
│   │   └── …
│   ├── progress-test-2/
│   ├── progress-test-3/
│   ├── progress-test-4/
│   └── progress-test-5/
└── student/                         ← FR-005 distinct location
    ├── index.html                   ← per-edition publication index (§3)
    ├── main/
    │   └── …
    ├── progress-test-1/
    │   └── …
    └── …
```

Cardinality:

- Exactly one shared landing page at `html/index.html`.
- Exactly two edition subdirectories: `html/instructor/`,
  `html/student/`. No other directories directly under `html/`.
- Exactly one per-edition publication index at
  `html/<edition>/index.html`.
- Each ditamap renders to `html/<edition>/<ditamap-stem>/` — the
  same `<ditamap-stem>` shape feature 001 / 002 already use.

## 2. Shared landing page (`html/index.html`)

### 2.1 Content shape

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>Published DITA output — choose an edition</title>
  </head>
  <body>
    <h1>Published DITA output</h1>
    <p>Generated {timestamp}</p>
    <ul>
      <li><a href="instructor/index.html"><strong>Instructor edition</strong></a>
        — full content, including answers, vessel names, and analysis sheets.</li>
      <li><a href="student/index.html"><strong>Student edition</strong></a>
        — exercises only, with answers, vessel names, and analysis sheets removed.</li>
    </ul>
  </body>
</html>
```

### 2.2 Contract clauses

- Exactly two links in the body, in this order: instructor edition,
  student edition. The link order is deterministic (no
  randomisation, no source-order surprise).
- Each link points at a path relative to `html/`, not absolute.
- The audience description text for each link is non-empty and
  contains enough context for a reviewer to tell the editions apart
  in one read (SC-004).
- `{timestamp}` is sourced from `SOURCE_DATE_EPOCH` when set
  (formatted as `YYYY-MM-DD HH:MM UTC`) and falls back to the fixed
  string `"unset"` otherwise — so two consecutive runs from the same
  environment produce byte-identical landing pages (FR-008).
- The page is the **only** file in `html/` whose contents are
  permitted to contain the word "Instructor" — see §4.

## 3. Per-edition publication index (`html/<edition>/index.html`)

### 3.1 Content shape

Reuses today's `write_root_index()` shape from feature 001 / 002,
scoped to one edition. One `<li>` per publication; link href points
to that publication's rendered subdirectory.

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>{Edition name} edition — published DITA output</title>
  </head>
  <body>
    <h1>{Edition name} edition</h1>
    <p>Generated {timestamp}</p>
    <ul>
      <li><a href="{ditamap-stem}/index.html">{Ditamap title}</a></li>
      <!-- …one li per publication, in the same order in both editions… -->
    </ul>
  </body>
</html>
```

### 3.2 Contract clauses

- The list of publications and their order MUST be identical across
  the two editions. A reviewer comparing the two `index.html` files
  side-by-side sees the same publications in the same order.
- `{Ditamap title}` is the *rendered* publication title for that
  edition:
  - instructor: full title including the "— Instructor Version"
    suffix from the audience-tagged `<ph>`.
  - student: title with the suffix stripped (just `"Progress Test 1"`,
    `"Main"`, etc.).
- The header text `"{Edition name} edition"` reads "Instructor
  edition" or "Student edition" respectively.
- `{timestamp}` follows the same rule as §2.

## 4. Substring guarantee under `html/student/`

A walker over `html/student/` MUST find zero occurrences of the
case-insensitive substring `"instructor"`:

- In any file content (every `*.html` and any other rendered file).
- In any directory name or file name in the tree.

The walker treats `html/index.html` separately — that file is
*permitted* to contain "Instructor" (it labels and links to the
instructor edition). The guarantee applies to everything reachable
from the student edition's per-edition index, not the shared
landing.

Verified by the test in `tests/test_publish_html.py`. FR-015 / SC-002.

## 5. URL parity

For every relative path `P` (from `html/`) under `html/instructor/`,
the path obtained by swapping the first segment
(`instructor` → `student`) MUST exist under `html/student/`, and
vice versa. FR-016.

Practically:

```
html/instructor/main/week-1-grams/gram-01/gram_01.html
  ↔
html/student/main/week-1-grams/gram-01/gram_01.html
```

The contents of the two files differ only in the elements the
audience filter strips; the *paths* themselves are byte-identical
below the edition segment.

A reader who has one URL can construct the other by swapping the
single edition segment. This is the cross-checking property the
instructor review workflow depends on.

## 6. Pre-existing deep-link behaviour

URLs that worked before this feature shipped (today: `html/main/…`,
`html/progress-test-1/…`) are not preserved. After this feature:

- `html/main/` no longer exists (moved under both
  `html/instructor/main/` and `html/student/main/`).
- `html/progress-test-N/` no longer exists at the top level.

The shared landing page (§2) is the supported way for any consumer to
re-derive the new URLs. No redirect shim is shipped (R8).

## 7. Idempotency

The full `html/` tree — shared landing page, both per-edition index
pages, every rendered topic — MUST be byte-identical across two
consecutive runs over the same DITA source. FR-008 / SC-006.

This is asserted in `tests/test_publish_html.py` by running the
publisher twice in a temp directory and comparing the resulting trees
file-by-file.

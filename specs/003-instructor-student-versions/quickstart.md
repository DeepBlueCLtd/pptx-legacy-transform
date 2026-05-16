# Quickstart: Instructor / Student Versions via DITA Audience Filtering

This walkthrough takes a fresh checkout (or a re-run after edits) and
produces both HTML editions from the existing DITA source, end to
end. It is the same path a maintainer follows to verify the feature
after any change — it exercises every Success Criterion in the spec.

## 0. Prerequisites

- Python 3.11 or later — no new third-party packages added by this
  feature.
- DITA-OT 4.x installed locally with a Java runtime on `PATH`.
  Acquisition/install path is documented in the project README
  (carried over from feature 001).
- The DITA source tree at `dita/` is up to date with the latest
  generator run. If unsure: re-run the generator (§2).

## 1. Verify the environment

```bash
python --version                   # expect 3.11+
python -m unittest discover tests/ # all green before any edits
```

The test suite includes the new assertions from this feature
(see Phase 1 contracts). All tests should pass before you start
making changes, and again after each change.

## 2. Regenerate the DITA source tree

The pre-feature `dita/` tree was generated with `instructor-` folder
prefixes (e.g. `dita/main/instructor-week-1-grams/`). After the
generator change ships, re-running it produces normalised slugs
(e.g. `dita/main/week-1-grams/`) and the new `dita/trainee.ditaval`
profile.

```bash
python generate_dita.py \
    --csv source.csv \
    --out dita/ \
    --image-root <path-to-source-pptx-tree> \
    --clean
```

Expected behaviour:

- `dita/main/` and `dita/main.ditamap` are regenerated.
- Every chapter folder under `dita/main/` whose original name
  carried the `"Instructor "` prefix is now slugified without it
  (`week-1-grams/`, `pub10-ed22b-updated/`, etc.).
- `dita/main.ditamap` no longer contains the `title=` attribute on
  `<map>` nor the `navtitle=` attribute on any `<topichead>`. Each
  ditamap now carries a `<title>` child element and each `<topichead>`
  a `<topicmeta>/<navtitle>` child.
- The audience-tagged "Instructor " prefix sits inside
  `<ph audience="-trainee">` on every chapter navtitle whose source
  name began with "Instructor ".
- Each ditamap's `<title>` element ends with
  `<ph audience="-trainee"> — Instructor Version</ph>`.
- The new file `dita/trainee.ditaval` is present and byte-identical
  to the form specified in `contracts/audience-filter.md` §1.2.

Spot-check one chapter and one ditamap:

```bash
ls dita/main/                              # no "instructor-" prefix anywhere
cat dita/main.ditamap | head -5            # <title>…</title>, no title= attribute
cat dita/trainee.ditaval                   # one <prop> rule, exclude trainee
```

## 3. Publish both editions

```bash
python publish_html.py \
    --dita dita/ \
    --out html/ \
    --dita-ot <path-to-dita-ot-install>
```

Expected behaviour:

- Two passes per ditamap: one without `--filter` (instructor), one
  with `--filter=dita/trainee.ditaval` (student).
- The publisher logs which filter (if any) was applied for each
  edition for each publication (FR-011).
- Final `html/` tree matches `contracts/html-edition-layout.md` §1:
  `html/index.html`, `html/instructor/<stem>/`, `html/student/<stem>/`.

## 4. Verify Success Criteria

### 4.1 SC-001 — gram-number-only headings in the student edition

Pick any gram known to carry a vessel name, e.g.
`html/student/main/progress-final-assessment-grams/gram-01/gram_01.html`:

```bash
grep -oE '<h1[^>]*>[^<]*</h1>' html/student/main/progress-final-assessment-grams/gram-01/gram_01.html
```

Expected: the heading text reads `"Gram 01"` (no separator, no
vessel name, no trailing whitespace anomalies).

Open the corresponding instructor-edition page in a browser:
`html/instructor/main/progress-final-assessment-grams/gram-01/gram_01.html`.
Expected: heading reads `"Gram 01 — FR TIE Bomber, Category 3, Tatooine"`
(or equivalent), with the em-dash separator from the source DITA.

### 4.2 SC-002 — zero "instructor" substring under `html/student/`

```bash
grep -ri 'instructor' html/student/ && echo "LEAKAGE" || echo "OK"
find html/student/ -iname '*instructor*' && echo "PATH LEAKAGE" || echo "OK"
```

Both checks must print `OK`.

### 4.3 SC-003 — no Analysis Sheet sections in the student edition

```bash
grep -ri 'Analysis Sheet' html/student/ && echo "LEAKAGE" || echo "OK"
```

Expected: `OK`. The instructor edition should retain every analysis
sheet:

```bash
grep -rcI 'Analysis Sheet' html/instructor/ | head
```

Expected: non-zero counts on most gram pages.

### 4.4 SC-004 — one-click navigation to either edition

Open `html/index.html` in a browser. Confirm two prominent links —
"Instructor edition" and "Student edition". Click each; verify the
per-edition index loads and shows every publication.

### 4.5 SC-005 — one invocation produces both editions

The single `publish_html.py` command in §3 produces both editions.
No manual config edit between runs, no per-edition flags.

### 4.6 SC-006 — idempotency

Run the publisher twice and diff:

```bash
python publish_html.py --dita dita/ --out html/ --dita-ot <…>
mv html html-first
python publish_html.py --dita dita/ --out html/ --dita-ot <…>
diff -r html-first html | head
```

Expected: zero diff output. (Set `SOURCE_DATE_EPOCH` to a fixed value
across both runs if comparing across shells.)

### 4.7 SC-007 — instructor edition unmistakably marked

Open any page under `html/instructor/`. Expected: the document title
(browser tab) and the in-page header read "{Publication} — Instructor
Version", with the suffix coming from the audience-tagged `<ph>`.

### 4.8 SC-008 — no regression in upstream tests

```bash
python -m unittest tests.test_mock_pptx tests.test_introspect_pptx tests.test_extract_to_csv
```

All upstream tests should pass. `tests.test_generate_dita` and
`tests.test_publish_html` carry the new assertions from this feature.

## 5. URL parity check

For any gram URL `html/instructor/X/Y/Z.html`, the URL obtained by
replacing `instructor/` with `student/` must exist and render the
filtered version of the same gram (FR-016):

```bash
INSTRUCTOR_URL=html/instructor/main/week-1-grams/gram-01/gram_01.html
STUDENT_URL=${INSTRUCTOR_URL/instructor\//student\/}
test -f "$INSTRUCTOR_URL" && test -f "$STUDENT_URL" && echo "OK"
```

Expected: `OK`.

## 6. Troubleshooting

- **`dita/trainee.ditaval` missing**: `publish_html.py` exits
  non-zero. Re-run `generate_dita.py` (§2) which writes the profile
  along with the rest of the source tree, or commit the profile by
  hand from the contract in `contracts/audience-filter.md` §1.2.
- **Leakage of "instructor" under `html/student/`**: the most likely
  cause is a chapter that wasn't normalised because its source name
  doesn't start with `"Instructor "` (case-insensitive) plus a single
  trailing space. Inspect the chapter string in `source.csv` and
  decide whether to update R4's prefix rule or fix the source data.
- **Idempotency test fails**: most likely cause is DITA-OT emitting a
  fresh timestamp in `<meta name="DC.date.created">`. Confirm the
  publisher's post-render scrub pass is removing or stamping that
  metadata (R7).

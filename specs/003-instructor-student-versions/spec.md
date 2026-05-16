# Feature Specification: Instructor / Student Versions via DITA Audience Filtering

**Feature Branch**: `claude/instructor-student-versions-6haQg`
**Created**: 2026-05-16
**Status**: Draft
**Input**: User description: "Let's discuss the instructor/student divide. We're going to use DITA 'audience' properties to allow publishing the student version without the 'answers' that are in the instructor version. We'll take 'sensitive' content with audience=-trainee. Then for the student version we'll publish with an exclude filter of -trainee. The bits that are excluded are: 'Instructor Version' in the document title/header content; for the title on each gram, the text after the colon in the title — so, everything after 'Gram 1:'. (Actually, drop the colon, too); the analysis sheet in the gram page. We should change the DITA extraction process to correctly tag the DITA data. We should also modify the publish process to publish two versions. We should also re-organise the html folder to store (and present) the data tidily."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A trainee can browse a version of the published material that contains no answers (Priority: P1)

A trainee opens the published HTML output and works through the grams as
exercises. They see each gram's number ("Gram 1", "Gram 12"…) but no
vessel name, classification, or location is revealed in the heading.
The analysis sheet — which records the correct answer and the
instructor's worked-through evaluation — is absent from every gram page.
Nothing in the document title or page header tells them they are
looking at a filtered version; the experience reads as a self-contained
student edition.

**Why this priority**: This is the deliverable the feature exists to
produce. Without a clean, answer-free trainee version, the pipeline
cannot be shipped to learners — instructors today have to manually
redact every gram. Shipping P1 alone is the MVP that unlocks distribution
to students.

**Independent Test**: Run the pipeline against the existing source
material, open the trainee-facing landing page, and confirm that for a
sample gram known to have a vessel name and analysis sheet (e.g.
`progress-test-1/gram-01`), the rendered page shows only the gram number
in the heading, contains no analysis-sheet section, and contains no
"Instructor Version" wording anywhere in the title bar or page header.
A full-text search of every page in the trainee output for the vessel
names and "Instructor" returns zero matches in title or heading
positions.

**Acceptance Scenarios**:

1. **Given** a gram whose source heading is "Gram 01" with vessel name
   "FR Prometheus, Category 1, Bespin" and an analysis sheet attached,
   **When** the trainee opens the rendered page in the student edition,
   **Then** the page heading reads "Gram 01" with no separator or
   vessel-name text following, and the page body shows the spectrogram(s)
   but no Analysis Sheet section.
2. **Given** a publication whose instructor edition is titled
   "Progress Test 1 — Instructor Version", **When** the trainee opens
   the same publication in the student edition, **Then** the document
   title and page header read "Progress Test 1" with no trailing
   "— Instructor Version" decoration.
3. **Given** the trainee landing page for the student edition,
   **When** the trainee navigates through every linked publication,
   **Then** no page reached from that landing page contains "Instructor
   Version" wording, a vessel-name decoration on any gram heading, or
   an Analysis Sheet section.

---

### User Story 2 — An instructor can browse the same content with every answer intact (Priority: P2)

An instructor or course author opens the instructor-facing landing page
and works through the same publications. Every gram heading shows the
gram number plus the vessel name and category ("Gram 01 — FR
Prometheus, Category 1, Bespin"). Every gram page includes its
Analysis Sheet. The document title and page header clearly mark the
output as the instructor edition so the author cannot confuse it with
the student edition while reviewing.

**Why this priority**: Instructors need the answers to teach against
the material and to verify the trainee filter has not over-stripped
content. The instructor edition is also the canonical authoring view —
it is what an author proofreads before sign-off.

**Independent Test**: Open the instructor landing page, navigate to the
same sample gram as Story 1, and confirm the heading carries the vessel
name, the Analysis Sheet section is present, and the document title /
page header is marked as the instructor edition.

**Acceptance Scenarios**:

1. **Given** the same source gram from Story 1 acceptance scenario 1,
   **When** the instructor opens the rendered page in the instructor
   edition, **Then** the page heading reads "Gram 01 — FR Prometheus,
   Category 1, Bespin" (or equivalent decoration of the vessel name)
   and the page body includes the Analysis Sheet section as a link or
   embedded asset.
2. **Given** a publication whose student edition is titled
   "Progress Test 1", **When** the instructor opens the same publication
   in the instructor edition, **Then** the document title and page
   header clearly indicate this is the instructor edition (e.g.
   "Progress Test 1 — Instructor Version").
3. **Given** an instructor reviews the rendered output and compares it
   to the source PowerPoint, **When** they spot-check ten grams across
   different publications, **Then** every vessel name and analysis-sheet
   link present in the source is present in the instructor edition.

---

### User Story 3 — A reviewer landing on the HTML output sees a tidy, audience-aware entry point (Priority: P3)

Today the publish process drops every publication's rendered HTML at
the root of `html/`, mixing instructor-only and trainee-safe content
into a single tree. After this feature, a reviewer who opens `html/`
encounters a clean top-level landing page that names the two editions
explicitly and lets them choose which one to enter. Within each
edition, the existing publication-by-publication index continues to
work; the path layout makes it obvious which edition any given URL
belongs to (so a stray bookmark to the instructor edition can never
accidentally be sent to a trainee).

**Why this priority**: Without this, instructors and trainees would be
sharing one undifferentiated `html/` tree, making accidental disclosure
of the instructor edition trivial. P3 turns the two outputs from
P1+P2 into a usable, separable distribution.

**Independent Test**: Open `html/index.html`. Confirm it presents both
editions distinctly, that following the "Student" link reaches a page
listing the same publications as the "Instructor" link, and that the
URL paths under each edition are clearly distinct (so a screenshot of
the address bar makes it obvious which edition is in view).

**Acceptance Scenarios**:

1. **Given** a fresh publish run, **When** a reviewer opens
   `html/index.html`, **Then** they see two clearly labelled entry
   points — "Instructor edition" and "Student edition" — with a short
   description of who each is for.
2. **Given** the reviewer clicks "Student edition", **When** the
   per-publication index for the student edition loads, **Then** every
   publication present in the source pipeline is listed, the visible
   ordering matches the instructor edition, and the URL is clearly
   scoped to the student edition.
3. **Given** the reviewer navigates from the student edition back to
   `html/index.html` and then into the instructor edition, **When**
   they open the same publication, **Then** the page renders with
   instructor-only content (vessel names, Analysis Sheets, "Instructor
   Version" labelling) — confirming both editions are independently
   reachable from one root.

---

### Edge Cases

- A gram has **no** vessel name recorded in the source CSV — the gram
  heading must read identically in both editions (just "Gram NN") and
  the audience filter must not introduce a stray separator character.
- A gram has **no** analysis sheet — the gram page must render
  identically in both editions and the audience filter must not leave
  an empty "Analysis Sheet" heading behind in the instructor edition.
- A publication's source title already contains the word "Instructor"
  embedded (today: chapter navtitles such as "Instructor Week 1 Grams",
  "Instructor Pub10_Ed22B_Updated"). In the *single* DITA source tree
  the displayed chapter navtitle MUST split into an audience-tagged
  "Instructor " prefix plus the audience-neutral remainder, and the
  chapter folder slug emitted in the source tree MUST drop the
  "Instructor " word entirely. The instructor edition then shows
  "Instructor Week 1 Grams" as the navtitle at the URL
  `instructor/main/week-1-grams/…`; the student edition shows
  "Week 1 Grams" as the navtitle at the URL
  `student/main/week-1-grams/…`. URL paths below the edition
  segment stay identical across editions — a reader with one
  edition's URL can transpose to the other by swapping the
  `instructor/` segment for `student/` (and vice-versa).
- A reviewer opens a deep-link URL that pre-dates this feature (e.g.
  `html/progress-test-1/...`). The behaviour after re-publish is well-
  defined: the path either redirects, 404s with a hint, or remains
  valid pointing to one specific edition — and this behaviour must not
  silently change between runs.
- A second publish run over the same DITA source produces byte-identical
  HTML in both editions (idempotency, consistent with the existing
  pipeline's R9 / FR-013 commitment from feature 001).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The DITA extraction process MUST tag every piece of
  instructor-only content with `audience="-trainee"` so that a single
  DITA-OT exclude filter (`-trainee`) produces the student edition.
- **FR-002**: The set of instructor-only content MUST include, at a
  minimum: (a) the vessel-name decoration on every gram title (the
  text that today follows "Gram NN" and identifies the answer);
  (b) the entire Analysis Sheet section of every gram page;
  (c) any "Instructor Version" wording on the publication-level title
  or page header.
- **FR-003**: The gram-title decoration MUST NOT be a bare colon-and-
  vessel-name pattern in the rendered output. The visible separator
  between "Gram NN" and the vessel name in the instructor edition
  MUST be human-readable text other than a colon (e.g. an en-dash with
  surrounding spaces), and MUST disappear entirely from the student
  edition along with the vessel name itself.
- **FR-004**: The publish process MUST produce two complete HTML
  editions from one DITA source tree in a single run: an instructor
  edition (no audience filter) and a student edition (with the
  `-trainee` audience excluded).
- **FR-005**: The two editions MUST be written to distinct, clearly
  named locations under `html/` such that no instructor-only file can
  be reached by following links that start at the student edition's
  entry point.
- **FR-006**: The `html/` tree MUST expose a single top-level landing
  page that names both editions and links into each, replacing the
  current single-tree, undifferentiated layout.
- **FR-007**: Each edition MUST retain a per-edition index page that
  lists every publication, equivalent in function to today's
  `html/index.html` but scoped to that edition.
- **FR-008**: Re-running the publish process over an unchanged DITA
  source MUST produce byte-identical HTML output in both editions
  (preserving the existing pipeline's idempotency guarantee).
- **FR-009**: The DITA source tree MUST remain the single source of
  truth: no manual editing of HTML output is required to produce
  either edition, and the instructor edition MUST contain every piece
  of content present in the source.
- **FR-010**: The student edition MUST NOT contain, in any rendered
  page, the word "Instructor" (case-insensitive, whether in the
  literal phrase "Instructor Version", a chapter navtitle, a page
  heading, or a navigation link label), any vessel-name decoration
  on a gram heading, or any Analysis Sheet section — verifiable by
  a full-text grep over the student-edition HTML output.
- **FR-011**: The publish process MUST log clearly which audience
  filter (if any) was applied for each edition, so a reviewer reading
  the build log can confirm which output was produced for which
  audience.
- **FR-012**: The feature MUST NOT break any existing pipeline stage:
  `mock_pptx.py`, `introspect_pptx.py`, `extract_to_csv.py`, and the
  signed-off `source.csv` contract remain unchanged. Only the DITA
  generator and the HTML publisher may be modified.
- **FR-013**: The pipeline MUST maintain exactly one DITA source tree.
  The two HTML editions MUST be produced by two publish-time
  invocations against the same source tree — one without an
  audience filter (instructor edition) and one with the `-trainee`
  audience excluded (student edition). No per-edition forking,
  copying, or post-publish rewriting of source DITA files is
  permitted.
- **FR-014**: The chapter folder slugs emitted into the single DITA
  source tree MUST NOT contain the substring "instructor"
  (case-insensitive). Where a source chapter name carries an
  "Instructor " prefix today, the prefix MUST be stripped before the
  slug is computed, so both editions render the affected chapter at
  the same path below the edition segment.
- **FR-015**: The student edition MUST NOT contain the substring
  "instructor" (case-insensitive) in any URL path beneath its
  top-level `student/` segment, in any rendered page body, in any
  page title, or in any navigation-link label — verifiable by
  walking the student-edition output tree and grepping its files
  and paths.
- **FR-016**: URL paths below the top-level edition segment MUST be
  identical across editions for every gram. A reader with the URL
  of a gram in one edition MUST be able to reach the same gram in
  the other edition by swapping the single edition segment
  (`instructor/` ↔ `student/`) — supporting cross-edition
  spot-checking during instructor review.

### Key Entities

- **Edition**: A complete, self-contained HTML rendering of every
  publication for one audience. Two editions exist: *instructor*
  (the unfiltered superset) and *student* (the `-trainee`-excluded
  subset). Each edition has its own root path under `html/` and its
  own publication index.
- **Audience-tagged element**: A DITA element (`<ph>`, `<section>`,
  topic-level marker) carrying `audience="-trainee"`. The DITA-OT
  exclude filter for the student edition strips every such element,
  removing it from the rendered HTML.
- **Publication**: One ditamap (the existing concept) — today there is
  `main` plus several `progress-test-N` ditamaps. Each publication
  renders once per edition.
- **Gram page**: One DITA topic per gram. Its title decoration and
  its Analysis Sheet section are the two largest carriers of audience-
  tagged content; the spectrogram tables themselves are audience-
  neutral and appear in both editions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of grams across every publication render with a
  visible gram-number-only heading in the student edition. No student-
  edition gram page exposes its vessel name, category, or location
  in the heading.
- **SC-002**: 0 occurrences of the substring "instructor"
  (case-insensitive) in the rendered HTML body, page title, link
  label, or URL path (below the top-level `student/` segment) of
  any page reachable from the student edition's landing page.
- **SC-003**: 0 Analysis Sheet sections rendered in the student
  edition; 100% of source-defined Analysis Sheets retained in the
  instructor edition.
- **SC-004**: A reviewer arriving at `html/index.html` can reach the
  per-publication index of either edition in one click and can tell
  which edition is in view from the URL alone.
- **SC-005**: The publish process produces both editions from one
  invocation. Producing both editions does not require manually
  re-running the pipeline or editing any config between runs.
- **SC-006**: Two consecutive publish runs over the same DITA source
  produce byte-identical HTML output in both editions (idempotency
  parity with the existing pipeline).
- **SC-007**: An instructor reviewing the instructor edition can
  identify any page as instructor-only within two seconds of opening
  it — without scrolling — because the document title or page header
  carries explicit "Instructor Version" wording.
- **SC-008**: The change does not regress the existing `unittest`
  suite for the upstream pipeline stages (`mock_pptx.py`,
  `introspect_pptx.py`, `extract_to_csv.py`).

## Assumptions

- The existing DITA topic structure (vessel name already inside
  `<ph audience="-trainee">`, Analysis Sheet already inside
  `<section audience="-trainee">`) is the right foundation. This
  feature extends — not redesigns — the audience-tagging convention
  already begun in `generate_dita.py`.
- The "Instructor Version" wording will be introduced by this feature.
  It is **not** assumed to be present in the source PPTX or the
  intermediate CSV; the DITA generator will emit it as part of the
  publication-level title decoration, wrapped in
  `audience="-trainee"`, so the trainee filter removes it.
- The chapter navtitles in `main.ditamap` (today: "Instructor Week 1
  Grams", "Instructor Pub10_Ed22B_Updated", etc.) carry the literal
  word "Instructor" baked into the navtitle. In the *single* DITA
  source tree this becomes: (a) chapter folder slugs with the
  "Instructor " word stripped (`week-1-grams/`,
  `pub10-ed22b-updated/`); (b) the displayed navtitle expressed as
  an audience-tagged "Instructor " prefix plus the audience-neutral
  remainder, so the instructor publish run renders the full
  "Instructor Week 1 Grams" navtitle while the student publish run
  (with `-trainee` excluded) renders just "Week 1 Grams".
- One source tree, two publish runs. The instructor edition is
  produced by running DITA-OT against the source tree with no
  audience filter; the student edition is produced by a second
  invocation of DITA-OT against the *same* source tree with a
  DITAVAL profile that excludes `-trainee`. No per-edition forking
  of the source DITA, no post-publish rewriting of folder names
  or links.
- URL paths below the top-level edition segment are identical
  across editions for every gram. The only differences between
  what an instructor and a trainee see at the same path are
  (a) the presence vs absence of vessel-name decoration in the
  page heading, (b) the presence vs absence of the Analysis Sheet
  section, and (c) the presence vs absence of the "Instructor "
  prefix on chapter navtitles and the "Instructor Version"
  decoration on document titles.
- The progress-test ditamaps (`progress-test-1` … `progress-test-5`)
  already strip the "Instructor" prefix from their `<map title="…">`
  attribute (today: "Progress Test 1"). The "Instructor Version"
  decoration this feature adds attaches *after* the existing title,
  not in front of it.
- Two parallel subtrees (`html/instructor/` and `html/student/`) under
  one shared `html/index.html` is the default layout decision for
  FR-005 / FR-006. Alternatives (a single tree with per-page audience
  toggling, query-string filtering at view time) are out of scope for
  the first cut.
- DITA-OT remains the publish engine. The exclude filter mechanism
  used here is the standard DITAVAL profile (`-trainee` excluded) so
  no custom rendering pipeline is introduced.
- The existing landing-page generator in `publish_html.py` (function
  `write_root_index`) is extended, not replaced — its publication-link
  shape is reused for each edition's per-edition index.
- The set of audience values in use stays small and binary: a single
  audience name (`trainee`) and the matching DITAVAL action
  (`exclude` for `-trainee`). A larger taxonomy (multiple cohorts,
  per-publication audience overrides) is out of scope.

## Out of Scope

- No new content audiences beyond *instructor* and *student*.
- No per-gram opt-out from the audience filter — every gram in every
  publication is filtered by the same rule.
- No change to the source-PPTX inspection, the CSV intermediate, or
  the sign-off workflow that produces `source.csv`.
- No change to the GramFrame spectrogram table contract — both
  editions render the same spectrogram blocks.
- No new always-on infrastructure (web app, server, watcher). The
  publish process remains a one-shot local invocation.

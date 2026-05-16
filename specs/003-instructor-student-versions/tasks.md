---

description: "Tasks for feature 003: instructor/student versions via DITA audience filtering"
---

# Tasks: Instructor / Student Versions via DITA Audience Filtering

**Input**: Design documents from `/specs/003-instructor-student-versions/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/audience-filter.md`, `contracts/html-edition-layout.md`, `quickstart.md`

**Tests**: Test-first. Tests are split between two layers — Python
`unittest` for DITA XML output (where `xml.etree` is the right tool)
and **Jest** for rendered HTML verification (where DOM-shaped
assertions read more naturally than `xml.etree` against an HTML
document). Each user story's test additions precede its implementation
tasks and MUST fail before implementation begins.

**Organization**: Tasks are grouped by user story. Each story is
independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story tag (US1 / US2 / US3)
- Every task description includes the exact target file path

## Path Conventions

Single-project layout (carried over from feature 001):

- Python scripts live at repository root
- Python tests live under `tests/`
- Python test fixtures live under `tests/fixtures/`
- **NEW**: Jest tests live under `tests/web/`
- DITA source tree lives at `dita/`
- HTML output tree lives at `html/`

All paths below are repository-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Stand up the Jest test layer so HTML verification tasks
have somewhere to land. None of these tasks change the Python pipeline.

- [ ] T001 [P] Create `package.json` at the repo root with
  `jest@^29` and `cheerio@^1` as `devDependencies`, a `"test": "jest"`
  npm script, and `"private": true` so it never publishes. Include
  `"name": "pptx-legacy-transform-web-tests"` and a one-line
  `"description"`.
- [ ] T002 [P] Create `jest.config.js` at the repo root:
  `rootDir: "./tests/web"`, `testEnvironment: "node"`,
  `testMatch: ["**/*.test.js"]`. Keep the file minimal and
  CommonJS-flavoured (the project has no other JS tooling to align
  with).
- [ ] T003 [P] Append `node_modules/`, `.jest-cache/`, and
  `package-lock.json` to `.gitignore` (the package-lock for a dev-
  only Jest setup adds churn without value; the test stack is
  evergreen).
- [ ] T004 [P] Add a "HTML output verification (Jest)" section to
  `README.md` explaining: prerequisite (`npm install` once), when to
  run (`npm test` after `python publish_html.py`), what it asserts
  (no-leakage grep, URL parity, gram-heading shape), and how it
  differs from the Python `unittest` suite (which covers DITA XML
  output and publisher orchestration).

**Checkpoint**: `npm install && npm test` runs (with zero tests
found) and exits 0.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The DITAVAL profile and the test fixture both user stories
depend on.

**⚠️ CRITICAL**: No user-story work can begin until this phase is
complete.

- [ ] T005 [P] Create `dita/trainee.ditaval` with the byte-exact
  content from `specs/003-instructor-student-versions/contracts/audience-filter.md`
  §1.2 (UTF-8, LF line endings, no BOM). One `<prop>` rule excluding
  `audience="trainee"`. This file is the only DITAVAL profile this
  feature ships.
- [ ] T006 [P] Create `tests/fixtures/audience_minimal.csv` covering
  the three audience-shape cases the Python tests will assert on:
  (a) one chapter whose name begins with `"Instructor "` (e.g.
  `"Instructor Week 1 Grams"`), (b) one chapter whose name does NOT
  (e.g. `"Plain Chapter"`), (c) one gram with `vessel_name` populated
  plus a `topic_type=analysis` row, and one gram with neither (to pin
  the edge case where the audience filter MUST NOT introduce a stray
  separator). Header row matches the existing `CSV_COLUMNS` tuple in
  `generate_dita.py` so the fixture is read without
  schema-mismatch errors.

**Checkpoint**: `dita/trainee.ditaval` is committed and grep-able; the
fixture CSV loads via the existing `read_csv()` helper without errors.

---

## Phase 3: User Story 1 — Trainee can browse a version with no answers (Priority: P1) 🎯 MVP

**Goal**: Produce a complete student edition HTML tree at
`html/student/` from one publish-time DITA-OT invocation, with no
"instructor" substring anywhere in its content, paths, gram headings,
or page titles. This is the deliverable the feature exists for.

**Independent Test**: Run `python publish_html.py --dita dita/
--out html/ --dita-ot <path>` and verify (a) `html/student/` exists
and contains every publication's rendered HTML, (b) a recursive
case-insensitive grep for `"instructor"` over every file and every
path component under `html/student/` returns zero hits, (c) at least
one known sample gram page (e.g. `progress-test-1/gram-01`) renders
with the heading `"Gram 01"` only and no Analysis Sheet section.

### Tests for User Story 1 (write FIRST — must fail before implementation)

- [ ] T007 [P] [US1] In `tests/test_generate_dita.py`, add three
  failing test methods asserting the new DITA shape:
  (a) `test_chapter_slug_strips_instructor_prefix` — runs the
  generator against `tests/fixtures/audience_minimal.csv` and asserts
  the emitted folder for "Instructor Week 1 Grams" is `week-1-grams/`
  (no `instructor-` prefix anywhere); (b) `test_map_title_uses_title_element` —
  asserts the generated ditamap has a `<title>` child of `<map>`
  containing the audience-tagged `<ph> — Instructor Version</ph>`
  suffix and NO `title=` attribute on the `<map>` element;
  (c) `test_topichead_uses_topicmeta_navtitle` — asserts each
  `<topichead>` carries `<topicmeta>/<navtitle>` with the
  audience-tagged `<ph audience="-trainee">Instructor </ph>` prefix
  for the "Instructor "-prefixed chapter, and a plain `<navtitle>`
  with no `<ph>` for the plain chapter, and NO `navtitle=` attribute
  on either `<topichead>`.
- [ ] T008 [P] [US1] In `tests/test_publish_html.py`, add a failing
  test method `test_student_edition_dita_ot_invocation` that uses
  `subprocess.run` mocking to assert: for each ditamap, the publisher
  calls DITA-OT with `--filter=<absolute-path-to>/dita/trainee.ditaval`,
  `--output=<staged-out>/student/<stem>/`, and `--format=html5`.
  Also assert the publisher logs a line containing `student` and
  the filter path for each ditamap (FR-011).
- [ ] T009 [P] [US1] Create `tests/web/student-edition.test.js` with
  failing Jest tests covering:
  (a) **SC-002 — no "instructor" content leakage**: walks every file
  under `html/student/` with a recursive helper, reads each as utf-8,
  asserts `.toMatch(/instructor/i)` is `false`;
  (b) **SC-002 — no "instructor" path leakage**: walks every directory
  + file name under `html/student/` and asserts none match
  `/instructor/i`;
  (c) **SC-001 — gram-number-only headings**: globs
  `html/student/**/gram_*.html`, parses each with cheerio, asserts
  `$('h1, h2').first().text().trim()` matches `/^Gram \d+$/`
  (no separator, no vessel name, no trailing whitespace);
  (d) **SC-003 — no Analysis Sheet sections**: greps every file
  under `html/student/` for the literal "Analysis Sheet" and asserts
  zero hits.
  All four tests will fail at this point — `html/student/` does not
  yet exist.

### Implementation for User Story 1

- [ ] T010 [US1] In `generate_dita.py`, add a `_normalise_chapter(raw: str) -> tuple[str | None, str, str]`
  helper that returns `(audience_prefix, display_remainder, slug)`,
  matching the `ChapterNormalisation` shape defined in
  `data-model.md` §4.1. Use case-insensitive leading-`"Instructor "`
  detection per research R4. Add a short docstring with the four
  table-driven examples from `data-model.md`. No other code in
  `generate_dita.py` changes in this task.
- [ ] T011 [US1] In `generate_dita.py`, replace every existing
  `slugify(row.get("chapter", ""))` call (currently in
  `_publication_root()` and `emit_main_ditamap()`) with a call to
  `_normalise_chapter()`, using `.slug` for path computation. This
  task drops the `instructor-` prefix from every chapter folder name
  emitted under `dita/main/`; nothing else changes.
- [ ] T012 [US1] In `generate_dita.py`, change `emit_main_ditamap()`
  and `emit_test_ditamap()` to emit
  `<map><title>{title-text}<ph audience="-trainee"> — Instructor Version</ph></title>...</map>`
  in place of `<map title="...">…</map>`. The title text is "Main" or
  "Progress Test N" exactly as today; the audience-tagged suffix is
  identical across all ditamaps. Removes the `title=` attribute from
  the `<map>` element entirely.
- [ ] T013 [US1] In `generate_dita.py`, change `emit_main_ditamap()`
  to emit each chapter as
  `<topichead><topicmeta><navtitle>{decoration}</navtitle></topicmeta>...<topicref/>...</topichead>`,
  where `{decoration}` is `<ph audience="-trainee">Instructor </ph>{display_remainder}`
  when `_normalise_chapter()` returns a non-None `audience_prefix`, or
  just the plain text when it returns `None`. Removes the `navtitle=`
  attribute from `<topichead>` entirely.
- [ ] T014 [US1] In `publish_html.py`, add a small `Edition` dataclass
  near the top of the module (matching `data-model.md` §1.1) with
  fields `name: str`, `output_subdir: str`, `ditaval: Path | None`,
  `description: str`. Define the module-level constant
  `EDITIONS = (Edition("instructor", "instructor", None, "..."), Edition("student", "student", Path("trainee.ditaval"), "..."))`.
  No callers yet — pure structural addition this task.
- [ ] T015 [US1] In `publish_html.py`, modify the `publish()` function
  to iterate over the student-edition entry in `EDITIONS`: for each
  ditamap, invoke DITA-OT with `--filter=<dita>/trainee.ditaval` and
  `--output=<staged-out>/student/<stem>/`. Log
  `[publish:student] {ditamap.name} -> {target} (filter={filter_path})`
  before each call. If `dita/trainee.ditaval` is missing the function
  returns non-zero with a clear error (no silent fallback). The
  instructor-edition entry is iterated over but the body of the loop
  is a stub call (`# wired up by T021`); this keeps US1 testable
  without the instructor pass.
- [ ] T016 [US1] Re-run `python generate_dita.py --csv source.csv
  --out dita/ --image-root <PPTX-source-tree> --clean` to refresh
  the committed DITA source tree with normalised chapter slugs and
  the new ditamap shape. Commit the regenerated `dita/` tree
  alongside the generator change. Expect: every chapter folder
  under `dita/main/` whose original name began with "Instructor "
  is renamed; every ditamap's first line changes from a `<map
  title="...">` opener to `<map><title>...</title>...</map>` opener.

### Verification for User Story 1

- [ ] T017 [US1] Run `python -m unittest discover tests/` from the
  repo root. All Python tests in `test_generate_dita.py` and
  `test_publish_html.py` should pass (including T007 and T008 added
  earlier). Pre-existing tests for feature 001 must also still pass
  (FR-012 / SC-008).
- [ ] T018 [US1] Run `python publish_html.py --dita dita/ --out html/
  --dita-ot <path>` against the full corpus, then `npm install &&
  npm test`. All four Jest tests added in T009 must pass. Confirms
  the student edition satisfies SC-001 / SC-002 / SC-003 against the
  real rendered output.

**Checkpoint**: User Story 1 is complete. The student edition can
ship — trainees have a clean, answer-free HTML view of every
publication. No instructor edition exists yet under `html/`.

---

## Phase 4: User Story 2 — Instructor can browse the same content with answers intact (Priority: P2)

**Goal**: Produce a complete instructor edition HTML tree at
`html/instructor/` from the same publish-time invocation that
produces the student edition. Verify URL parity (FR-016) and the
"Instructor Version" marker (SC-007).

**Independent Test**: After `publish_html.py` runs, verify that
`html/instructor/` exists, every gram URL under `html/student/` has a
sibling at the same path under `html/instructor/`, and a sample gram
page (e.g. `progress-test-1/gram-01`) renders with the full
"Gram 01 — FR Prometheus, Category 1, Bespin" heading and includes
its Analysis Sheet section.

### Tests for User Story 2 (write FIRST — must fail before implementation)

- [ ] T019 [P] [US2] In `tests/test_publish_html.py`, add a failing
  test method `test_instructor_edition_dita_ot_invocation` that
  asserts: for each ditamap, the publisher ALSO calls DITA-OT
  *without* `--filter` and with `--output=<staged-out>/instructor/<stem>/`.
  The publisher logs `[publish:instructor] {ditamap.name} -> {target}
  (filter=none)` before each instructor pass. Both passes happen in
  the same publisher invocation (SC-005).
- [ ] T020 [P] [US2] Create `tests/web/instructor-edition.test.js`
  with failing Jest tests covering:
  (a) **SC-007 — instructor pages clearly marked**: globs
  `html/instructor/**/*.html`, parses each with cheerio, asserts the
  document `<title>` element OR the first heading contains the
  literal substring "Instructor Version";
  (b) **FR-016 — URL parity**: walks every file under
  `html/instructor/`, computes the sibling path under
  `html/student/`, asserts the sibling exists. Then walks every file
  under `html/student/` and asserts the instructor-side sibling
  exists too. Symmetric round-trip.
  (c) **SC-003 — Analysis Sheets preserved for instructors**: for at
  least three sample grams known to carry analysis sheets in the
  source, asserts the rendered instructor page contains a heading
  with text "Analysis Sheet".

### Implementation for User Story 2

- [ ] T021 [US2] In `publish_html.py`, wire up the instructor-edition
  branch left stubbed in T015: for each ditamap, invoke DITA-OT
  with NO `--filter` and `--output=<staged-out>/instructor/<stem>/`.
  Same logging convention as the student pass but the
  `(filter=none)` suffix indicates no filter applied.
- [ ] T022 [US2] In `publish_html.py`, update the post-publish
  prettify pass: `prettify_tree()` now walks `html/instructor/` AND
  `html/student/` (not the old single `html/` root). Confirm the
  walk handles both subtrees in one call so the existing
  count-of-files log line is the sum across both editions.

### Verification for User Story 2

- [ ] T023 [US2] Re-run `python -m unittest discover tests/` + `npm
  test`. All tests green, including T019 and T020 from above. Spot-
  check by opening
  `html/instructor/main/progress-final-assessment-grams/gram-01/gram_01.html`
  and the corresponding `html/student/.../gram_01.html` in a browser
  — the URLs differ only by the edition segment, the content differs
  only in the audience-filtered elements.

**Checkpoint**: User Stories 1 AND 2 both work. Instructors and
trainees have parallel HTML editions, audience-filtered correctly. No
shared landing page yet — reviewers reach each edition by guessing the
URL.

---

## Phase 5: User Story 3 — Reviewer landing on `html/` sees a tidy, audience-aware entry point (Priority: P3)

**Goal**: Replace the old single `html/index.html` with a shared
landing page that explicitly names both editions and links into each,
plus per-edition publication-index pages at
`html/{instructor,student}/index.html`.

**Independent Test**: Open `html/index.html`, see two prominent links
("Instructor edition", "Student edition") each with a one-sentence
description, click each, land on a publication list, click any
publication, reach the same rendered topic tree US1 and US2 produced.

### Tests for User Story 3 (write FIRST — must fail before implementation)

- [ ] T024 [P] [US3] In `tests/test_publish_html.py`, add a failing
  test method `test_shared_landing_page_shape` asserting:
  `html/index.html` exists; contains exactly two `<a>` elements in
  body order pointing at `instructor/index.html` and
  `student/index.html` respectively; the link text labels them
  unambiguously ("Instructor edition", "Student edition"); a
  `Generated …` line is present; the page is byte-deterministic given
  a fixed `SOURCE_DATE_EPOCH`.
- [ ] T025 [P] [US3] Create `tests/web/landing-page.test.js` with
  failing Jest tests covering:
  (a) **SC-004 — one-click navigation**: parses `html/index.html`,
  asserts exactly two `<a>` elements pointing at
  `instructor/index.html` and `student/index.html`, each with an
  audience description of at least 20 characters following the link
  text;
  (b) **per-edition index lists every publication**: parses
  `html/instructor/index.html` and `html/student/index.html`,
  collects the publication links from each, asserts the two lists
  contain the same set of `<stem>` values (URL parity at the index
  level), in the same order;
  (c) **per-edition index titles reflect the edition**: the
  instructor index has "Instructor" in its `<h1>`; the student index
  does NOT.

### Implementation for User Story 3

- [ ] T026 [US3] In `publish_html.py`, rename `write_root_index()` to
  `write_edition_index(out_subdir, edition, entries, generated_at)`.
  The function now takes an `Edition` instance and writes its index
  to `out_subdir/index.html`. Heading text reads
  "{edition.name.title()} edition". Link hrefs are
  `{stem}/index.html` (unchanged).
- [ ] T027 [US3] In `publish_html.py`, add a new function
  `write_shared_landing(out_root, editions, generated_at)` that
  writes `html/index.html` matching the shape pinned in
  `specs/003-instructor-student-versions/contracts/html-edition-layout.md`
  §2.1. Two `<li>` items in deterministic order (instructor first,
  student second), each linking to its per-edition index with an
  inline audience description sourced from `edition.description`.
- [ ] T028 [US3] In `publish_html.py`'s `main()`, after the two
  DITA-OT passes complete: call `write_edition_index()` once for the
  instructor entries and once for the student entries (writing to
  `html/instructor/index.html` and `html/student/index.html`
  respectively), then call `write_shared_landing()` once (writing to
  `html/index.html`). Replace the existing single
  `write_root_index()` call at the end of `main()`.

### Verification for User Story 3

- [ ] T029 [US3] Re-run `python -m unittest discover tests/` + `npm
  test`. All tests green. Open `html/index.html` in a browser:
  confirm both editions are reachable from the top-level page in one
  click each (SC-004).

**Checkpoint**: All three user stories are complete. The dual-edition
output is shippable: instructors and trainees have their own clearly-
named entry point into a tidy, audience-aware HTML tree.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Idempotency (FR-008 / SC-006), documentation, end-to-end
validation.

- [ ] T030 In `publish_html.py`, extend `prettify_tree()` (or add a
  sibling pass invoked right after it) to walk every emitted
  `*.html` file and strip the `<meta name="DC.date.created" …>`
  element and any DITA-OT-generated `<!-- Generated by DITA-OT … -->`
  comment that carries a wall-clock timestamp. This is the only
  known non-deterministic field in DITA-OT 4.x HTML5 output (R7).
- [ ] T031 In `tests/test_publish_html.py`, add a failing-then-passing
  test `test_idempotent_publish_run` that: runs the publisher twice
  into separate temp directories with a fixed `SOURCE_DATE_EPOCH`,
  collects sha256 hashes of every file under each `html/` tree,
  asserts the two hash maps are equal (SC-006).
- [ ] T032 [P] Create `tests/web/idempotency.test.js` with a Jest
  companion test that walks `html/instructor/` and `html/student/`,
  computes a sha256 of each file's contents, snapshots the hash map
  via `expect(hashMap).toMatchSnapshot()`. The first run records the
  snapshot; subsequent runs over the same DITA source MUST match it
  (developer-visible signal when a non-deterministic change creeps
  in).
- [ ] T033 [P] Update `README.md`'s "Run the pipeline" section to
  describe the new dual-edition output layout (cite
  `contracts/html-edition-layout.md` §1) and document the
  `npm install` / `npm test` step for HTML-output verification. Add
  a short note that the old top-level `html/main/`, `html/progress-test-N/`
  paths no longer exist (R8) — the new shared landing at
  `html/index.html` is the authoritative entry point.
- [ ] T034 Run the complete quickstart at
  `specs/003-instructor-student-versions/quickstart.md` end-to-end
  against the full corpus. Walk through §4.1 through §4.8 (every
  SC-001 … SC-008 verification) and tick each off. Capture any
  deviations as follow-up backlog items rather than silent fixes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — can start immediately.
- **Foundational (Phase 2)**: depends on Setup; blocks all user
  stories.
- **User Story 1 (Phase 3)**: depends on Foundational.
- **User Story 2 (Phase 4)**: depends on User Story 1 (US2 wires up
  the publisher branch US1 stubs out in T015; see T021). The two
  stories are mostly parallel work but the shared `publish_html.py`
  modifications serialise them.
- **User Story 3 (Phase 5)**: depends on User Story 2 (the per-
  edition indexes assume both editions are produced).
- **Polish (Phase 6)**: depends on all three user stories.

### User Story Dependencies

The three stories share `publish_html.py` and therefore cannot be
parallelised across developers in this codebase. They MUST be
implemented in priority order (P1 → P2 → P3) so the publisher's
diff history stays clean.

### Within Each User Story

- Tests are added first (T007/T008/T009 for US1, T019/T020 for US2,
  T024/T025 for US3) and MUST fail before implementation begins.
- Inside `generate_dita.py` (US1 only): `_normalise_chapter()`
  helper first (T010), then its callers (T011), then the ditamap
  shape changes (T012, T013). T011-T013 all edit the same file —
  sequential.
- Inside `publish_html.py`: structural additions (`Edition`
  dataclass, T014) before behavioural changes (T015, T021, T022,
  T026, T027, T028). All edits touch one file — sequential.
- Verification tasks (T017/T018, T023, T029, T034) run last in their
  respective phases.

### Parallel Opportunities

Independent (different files, no incomplete dependencies) — safe to
do simultaneously when staffed:

- **Phase 1**: T001 / T002 / T003 / T004 all four in parallel.
- **Phase 2**: T005 / T006 in parallel.
- **US1 tests**: T007 / T008 / T009 in parallel (three different
  files).
- **US2 tests**: T019 / T020 in parallel.
- **US3 tests**: T024 / T025 in parallel.
- **Polish**: T032 / T033 in parallel.

Sequential within a single file:

- `generate_dita.py` edits (T010 → T011 → T012 → T013).
- `publish_html.py` edits (T014 → T015 → T021 → T022 → T026 → T027 →
  T028 → T030).
- `tests/test_publish_html.py` edits (T008 → T019 → T024 → T031).

---

## Parallel Example: User Story 1 — adding the failing tests

```bash
# Three new test surfaces, three different files, no shared edits — all parallel:
Task: "T007 add failing DITA-shape tests in tests/test_generate_dita.py"
Task: "T008 add failing publisher-invocation test in tests/test_publish_html.py"
Task: "T009 create tests/web/student-edition.test.js with four failing Jest tests"
```

After all three fail as expected, implementation tasks T010 → T015 are
sequential within `generate_dita.py` and `publish_html.py`.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup — 4 tasks).
2. Complete Phase 2 (Foundational — 2 tasks).
3. Complete Phase 3 (User Story 1 — 12 tasks).
4. **STOP and VALIDATE**: trainees have a clean answer-free HTML
   view at `html/student/`. The instructor edition does not yet
   exist; reviewers cannot yet cross-check from a shared landing
   page. Both shortcomings are acceptable for the MVP cut.

### Incremental Delivery

1. Setup + Foundational → infrastructure ready.
2. Add US1 → ship the student edition (MVP, SC-001/002/003 pass).
3. Add US2 → ship the instructor edition (SC-007 + URL parity).
4. Add US3 → ship the shared landing page (SC-004).
5. Polish → idempotency lock-in (SC-006), README, end-to-end.

### Single-Developer Strategy

This feature's three stories share `publish_html.py` and
`generate_dita.py`, so a single developer working sequentially is
the natural shape. The user-story phasing exists for testability
and review — each phase is a complete, demoable step — not for
parallel staffing.

---

## Notes

- `[P]` tasks edit different files and have no incomplete
  dependencies.
- `[Story]` tag traces each task to the user story it ships.
- Each user-story phase MUST end with passing tests across both
  layers (Python `unittest` and Jest) before the next phase begins.
- Tests for a phase are committed in one or more failing commits
  first, then the implementation commit(s) flip them green — keeps
  the commit history readable and the test-first discipline visible
  in the diff.
- Avoid: editing `publish_html.py` and `generate_dita.py` in the
  same commit; mixing test additions with implementation in one
  task; touching upstream pipeline files (`mock_pptx.py`,
  `introspect_pptx.py`, `extract_to_csv.py`, `source.csv`) — feature
  scope explicitly forbids this (FR-012).
- The committed `dita/` tree gets regenerated as T016. The diff is
  large (every chapter folder under `main/` is renamed) but
  mechanical; the commit message should call out the regen so a
  future reviewer doesn't think the source content changed.

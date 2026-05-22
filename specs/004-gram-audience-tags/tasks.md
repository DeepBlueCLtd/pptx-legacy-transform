---
description: "Task list for feature 004 — per-gram audience tags via CSV `audience` column"
---

# Tasks: Per-Gram Audience Tags via CSV `audience` Column

**Input**: Design documents from `/specs/004-gram-audience-tags/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Branch**: `claude/zealous-tesla-lqGEa`

**Tests**: Required. Plan §"Constitution Check" specifies test-first;
each script change is paired with assertions added to its existing
test module *before* the source edit lands. Web test suite under
`tests/web/` is rewritten/extended to match the new three-edition
shape.

**Organization**: Tasks are grouped by user story to enable
independent implementation and testing. Within each story,
test-first ordering: extend the test module → edit the source file
to make the new assertions pass.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project at repository root: `*.py` scripts at root,
Python tests under `tests/`, web tests under `tests/web/`, DITA
output under `dita/`, HTML output under `html/`, specification docs
under `specs/004-gram-audience-tags/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pre-implementation review of design artefacts; no
project-init tasks needed (this feature edits four existing
scripts in an existing repo).

- [ ] T001 Re-read the corrected design artefacts end-to-end and confirm no further plan drift before coding starts: `specs/004-gram-audience-tags/plan.md`, `specs/004-gram-audience-tags/spec.md`, `specs/004-gram-audience-tags/research.md`, `specs/004-gram-audience-tags/data-model.md`, `specs/004-gram-audience-tags/contracts/audience-csv-column.md`, `specs/004-gram-audience-tags/contracts/audience-dita-topicref.md`, `specs/004-gram-audience-tags/contracts/html-edition-trio.md`, `specs/004-gram-audience-tags/quickstart.md`
- [ ] T002 [P] Verify the baseline test suite is green before any edits: run `python -m unittest discover tests/` and confirm zero failures; capture the count for the regression baseline (SC-005)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-cutting machinery that every user story depends
on — the CSV column wiring (extractor writer + generator reader)
and the DITAVAL profile emitter. Without these, no user story can
be exercised end-to-end.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Test-first assertions for the foundational seam

- [ ] T003 [P] Extend `tests/test_extract_to_csv.py` with a test asserting `CSV_COLUMNS` is exactly 17 entries and the 17th is `"audience"`, and that every row written by the extractor carries an `audience` key (empty string when no tag was present)
- [ ] T004 [P] Extend `tests/test_extract_to_csv.py` with tests for `_strip_audience_tags` (or whatever the new helper is named) covering: no brackets → empty; one bracket → single token; two adjacent brackets `[-own][-other]` → `"-own -other"`; two whitespace-separated brackets `[-own] [-other]` → `"-own -other"`; bracket-only right side `"Gram 7: [-other]"` → vessel_name empty + audience `"-other"`; descriptors with unrecognised tokens like `[note]` → audience `"note"` (extractor doesn't gate vocabulary)
- [ ] T005 [P] Extend `tests/test_generate_dita.py` with a test that a 16-column legacy CSV (no `audience` header) is accepted by the generator and produces topicrefs with no `audience` attribute on any of them
- [ ] T006 [P] Extend `tests/test_generate_dita.py` with a test that `write_ditaval_profiles(out_dir)` writes exactly three files to `out_dir` — `trainee.ditaval`, `student-own.ditaval`, `student-other.ditaval` — each parseable as XML and carrying the expected `<prop att="audience" …>` rules per `contracts/audience-dita-topicref.md` §4

### Foundational source changes

- [ ] T007 Extend `_split_descriptor` in `extract_to_csv.py` to return `(gram_id, vessel_name, audience)` and add the helper `_strip_audience_tags(text) -> (head, audience)` that repeatedly strips trailing `[ … ]` groups (regex `r"\s*\[([^\[\]]+)\]\s*$"`) per research.md R1; preserve source-order joining with single spaces
- [ ] T008 Append `"audience"` as the 17th entry of `CSV_COLUMNS` in `extract_to_csv.py` and update every `Gram`-row dict constructor (analysis row + GLC row builders around lines 498 / 523) to write the parsed `audience` value into the new key on every row produced from that gram
- [ ] T009 Rename `write_trainee_ditaval` → `write_ditaval_profiles` in `generate_dita.py` (line 710); update its caller at line 810; emit three sibling files (`trainee.ditaval` unchanged, plus new `student-own.ditaval` and `student-other.ditaval`) per `contracts/audience-dita-topicref.md` §4.1–4.3; keep the module-level `TRAINEE_DITAVAL` string and add `STUDENT_OWN_DITAVAL` / `STUDENT_OTHER_DITAVAL` constants alongside it
- [ ] T010 Update the generator's CSV reader in `generate_dita.py` to tolerate both 15-column and 16-column CSV headers (`row.get("audience") or ""` per research.md R10), and pass the per-row audience value through to the gram-grouping pass
- [ ] T011 Update `publish_html.py`'s startup precondition check (line 847) from "trainee.ditaval must exist" to "all three DITAVAL profiles (`trainee.ditaval`, `student-own.ditaval`, `student-other.ditaval`) must exist in the dita staging tree; otherwise exit non-zero with the missing-file path in the error message"

**Checkpoint**: After Phase 2 the extractor emits the audience
column, the generator round-trips it (without yet emitting on
topicrefs), and three DITAVAL files are written — but the publisher
still produces the two-edition layout. End-to-end behaviour is
unchanged. T003–T006 should pass; the baseline test suite stays
green.

---

## Phase 3: User Story 1 — Week 3 substitution (Priority: P1) 🎯 MVP

**Goal**: A Week 3 PPTX with `[-own]` and `[-other]` tags on its
last two grams publishes to two student editions that omit one of
the two grams each, with both editions showing the same total
gram count.

**Independent Test**: Run §6 of `quickstart.md` after a full
pipeline run — count grams in `html/student-own/progress-test-3/index.html`
and `html/student-other/progress-test-3/index.html`; both counts
equal; `diff` of the surviving gram hrefs shows exactly the two
tagged grams swapping in/out.

### Test-first assertions for User Story 1

- [ ] T012 [P] [US1] Extend `tests/test_mock_pptx.py` with `test_week_3_carries_audience_markers`: build the mock Week 3 PPTX with `--seed 0`, parse its second grams slide, assert the penultimate gram's descriptor ends with `[-other]` and the last gram's descriptor ends with `[-own]`
- [ ] T013 [US1] Delete `test_no_fr_variant_drops_fr_prefix` from `tests/test_mock_pptx.py` (lines 97–107) — the publication it tested (`Instructor Progress Test 3 Grams No FR`) is removed in T015 and the assertion no longer has a target
- [ ] T014 [P] [US1] Extend `tests/test_generate_dita.py` with a test that a CSV row carrying `audience="-other"` produces a topicref with `audience="-other"` on the matching `<topicref>` inside the publication's ditamap, and that the topic file itself (the `<topic>` root) carries no audience attribute (FR-005, FR-006); cover both `emit_main_ditamap` (Week 3 chapter inside main.ditamap) and `emit_test_ditamap` (progress-test-3.ditamap)
- [ ] T015 [P] [US1] Extend `tests/test_generate_dita.py` with a test that a row whose `audience` cell is empty produces a topicref with **no** `audience` attribute (not `audience=""`)
- [ ] T016 [P] [US1] Rewrite `tests/web/student-edition.test.js` as two describe-blocks: `describe("student-own edition", …)` loads `html/student-own/progress-test-3/index.html` and asserts the `-own`-tagged gram is absent from index links while the `-other`-tagged gram is present; `describe("student-other edition", …)` is symmetric
- [ ] T017 [P] [US1] Update `tests/web/instructor-edition.test.js`'s URL-parity check: replace the single student-vs-instructor comparison with two passes (one per student edition) where each surviving path under `html/student-{own,other}/` is asserted to exist at the same path under `html/instructor/`
- [ ] T018 [P] [US1] Extend `tests/test_publish_html.py` with a test that after a publish run the directories `html/instructor/`, `html/student-own/`, `html/student-other/` exist and `html/student/` does NOT
- [ ] T019 [P] [US1] Extend `tests/test_publish_html.py` with a Week 3 substitution test: parse each student edition's `progress-test-3/index.html`, count gram `<a>` links, assert the two counts are equal AND the symmetric-difference of href sets has exactly two members (the two tagged grams)

### Source changes for User Story 1

- [ ] T020 [US1] Remove the `Publication("Instructor Progress Test 3 Grams No FR", FAMILY_TEST, no_fr=True)` entry from the `PUBLICATIONS` tuple in `mock_pptx.py` (line 102); retain the `no_fr` field on the `Publication` dataclass and the `"FR "`-prefix logic in `_pick_descriptor` per research.md R7
- [ ] T021 [US1] In `mock_pptx.py` `_pick_descriptor` (around lines 375–383), add a deterministic Week-3 audience-marker planter: when the publication name is exactly `"Instructor Week 3 Grams"` and the gram position is the last gram of the second grams slide, append ` [-own]` to the returned descriptor; when it's the second-to-last gram of the second slide, append ` [-other]`. The function signature may need the gram's position-on-slide passed through from the caller around line 463
- [ ] T022 [US1] In `generate_dita.py`, add the gram-grouping consistency check: while grouping CSV rows by `(publication, chapter, gram_id)` (the pass that already shares `topic_filename`), assert the set of whitespace-normalised `audience` values across the group has exactly one element; on violation raise a named exception whose message includes the publication, chapter, gram_id, and the conflicting values per data-model.md §1.3
- [ ] T023 [US1] In `generate_dita.py` `emit_main_ditamap` (line 628) and `emit_test_ditamap` (line 678), pass the per-gram audience value to `ET.SubElement(..., "topicref", {...})`: when audience is non-empty add `"audience": audience` to the attribute dict; when empty omit the key entirely (do NOT emit `audience=""`)
- [ ] T024 [US1] In `publish_html.py` replace the two-entry `EDITIONS` tuple (lines 69–85) with three entries: `instructor` (ditaval=None), `student-own` (ditaval=Path("student-own.ditaval")), `student-other` (ditaval=Path("student-other.ditaval")); update each `Edition.description` to a one-sentence audience-purpose string suitable for the landing page per data-model.md §5.1
- [ ] T025 [US1] In `publish_html.py` update the module docstring (around lines 50–60) and `run_pipeline_for_ditamap` docstring (around line 786) to describe the three-edition layout (`instructor/` + `student-own/` + `student-other/`) and the corresponding `--filter=` arguments per `contracts/audience-dita-topicref.md` §5
- [ ] T026 [US1] In `publish_html.py` `write_shared_landing` (line 707) update the title/description text to introduce three editions (was: two); the loop over `editions` (line 722) already handles N entries, so the iteration logic is unchanged — only the surrounding chrome copy is touched
- [ ] T027 [US1] Regenerate `source.csv` end-to-end from the mock corpus: `python mock_pptx.py --out mock_pptx_data --seed 0 && python extract_to_csv.py --source mock_pptx_data --out source.csv`; commit the regenerated file (17 columns, No-FR rows removed, Week 3 last two grams carrying `-own` / `-other` cells)
- [ ] T028 [US1] Regenerate the committed DITA tree under `dita/` by running `python generate_dita.py --csv source.csv --out dita`; verify by `grep -E 'topicref href=.*audience' dita/progress-test-3.ditamap` and confirm the new `student-own.ditaval` / `student-other.ditaval` siblings appear next to `trainee.ditaval`; commit the regenerated tree
- [ ] T029 [US1] Add per-publication audience-tag-count logging in `generate_dita.py` (FR-015 / SC-001): after emitting each ditamap, count how many topicrefs received an `audience=` attribute and log one INFO line per publication naming the publication and the distinct tokens applied
- [ ] T030 [US1] Run `quickstart.md` §3–§6 end-to-end and confirm the substitution behaviour matches SC-001 (student-own omits the `-own` gram; student-other omits the `-other` gram; counts equal; `diff` shows exactly the two swapped hrefs)

**Checkpoint**: User Story 1 fully working — MVP shippable. T012,
T014–T019 should pass. The mock corpus reflects the real PPTX's
Week 3 markers; the published HTML carries the substitution.

---

## Phase 4: User Story 2 — Author broadens tagging via one CSV cell (Priority: P1)

**Goal**: An author edits a single `audience` cell in `source.csv`,
re-runs `generate_dita.py` + `publish_html.py`, and the named gram
disappears from the targeted student edition's index while
remaining in the other editions.

**Independent Test**: Run §10 of `quickstart.md` — pick a gram with
empty `audience`, set its cells to `-other` across every row of the
gram, re-run the generator + publisher, verify the gram is missing
from `html/student-other/<publication>/index.html` but present in
`html/student-own/` and `html/instructor/`.

### Test-first assertions for User Story 2

- [ ] T031 [P] [US2] Extend `tests/test_generate_dita.py` with a test that two CSV rows of the same `(publication, chapter, gram_id)` carrying conflicting `audience` values raise the named exception added in T022 — assert the exception message contains the publication, chapter (or empty string), gram_id, and BOTH conflicting values (SC-007)
- [ ] T032 [P] [US2] Extend `tests/test_generate_dita.py` with a test that an `audience` value containing a no-leading-hyphen include-style token (e.g. `"own"`) is flagged as an authoring error and fails the build with a clear message (FR-016 edge-case bullet, `contracts/audience-csv-column.md` §4 last paragraph, `contracts/audience-dita-topicref.md` §2 last row)
- [ ] T033 [P] [US2] Extend `tests/test_generate_dita.py` with a test that an unrecognised hyphen-prefixed token (e.g. `"-foo"`) is emitted verbatim on the topicref AND a WARNING is logged naming the gram and the token; the build proceeds without error (FR-016, research.md R8)
- [ ] T034 [P] [US2] Extend `tests/test_generate_dita.py` with a test that an `audience` cell carrying non-canonical whitespace (`"  -own   -other  "`) is whitespace-normalised before emission (the topicref receives `audience="-own -other"`); two consecutive runs over the same human-edited CSV produce byte-identical ditamap output (FR-014 / SC-004 for the CSV-edit case)
- [ ] T035 [P] [US2] Extend `tests/test_generate_dita.py` with a test that a CSV row carrying `audience="-own -other"` produces a topicref with `audience="-own -other"` AND that the resulting publication, after DITA-OT runs both student profiles, omits the gram from BOTH student editions while keeping it in the instructor edition (FR-011)

### Source changes for User Story 2

- [ ] T036 [US2] In `generate_dita.py` add the per-row audience normalisation pass: `audience = " ".join((row.get("audience") or "").strip().split())` before grouping; this is the single normalisation point referenced by T022's consistency check and by T031–T035
- [ ] T037 [US2] In `generate_dita.py` add the audience-token vocabulary gate: maintain a constant `RECOGNISED_AUDIENCE_TOKENS = ("-trainee", "-own", "-other")`; for every non-empty audience cell, split on whitespace and inspect each token: a token with no leading hyphen → raise a build-failing named error (T032); a hyphen-prefixed token not in the allow-list → log a WARNING and continue (T033); a recognised token → no log
- [ ] T038 [US2] Run `quickstart.md` §10 end-to-end (pick an untagged gram, set its `audience` cell to `-other` across all rows, re-run generator + publisher) and confirm the gram is absent from `html/student-other/` and present in the other two editions (SC-002)

**Checkpoint**: User Story 2 fully working. T031–T035 should pass.
The author affordance (one cell, three editions update correctly)
is demonstrated end-to-end.

---

## Phase 5: User Story 3 — No-FR publication eliminated (Priority: P2)

**Goal**: After the pipeline runs, no folder, ditamap, HTML page,
or CSV row references "Progress Test 3 Grams No FR" anywhere in
the corpus or its outputs.

**Independent Test**: Run `quickstart.md` §7 — case-insensitive
grep for `"no.fr"` and `"no fr"` across `html/`, `dita/`,
`source.csv`, and `mock_pptx.py` returns zero matches.

### Test-first assertions for User Story 3

- [ ] T039 [P] [US3] Extend `tests/test_publish_html.py` with a "no fr absent" test: after a publish run, a recursive grep across `html/` (or equivalent in-Python walk) for the case-insensitive substring `"no fr"` returns zero matches (SC-003)
- [ ] T040 [P] [US3] Extend `tests/test_publish_html.py` with an idempotency test covering all three editions: two consecutive `publish_html.py` runs over the same DITA source produce byte-identical files under `html/instructor/`, `html/student-own/`, and `html/student-other/` (FR-014 / SC-004); use the existing idempotency helper if there is one, otherwise compare file-by-file via hashlib
- [ ] T041 [P] [US3] Extend `tests/test_mock_pptx.py` with a test that the regenerated `PUBLICATIONS` tuple has exactly 10 entries (was 11), and no entry's name contains the case-insensitive substring `"no fr"`

### Source changes for User Story 3

- [ ] T042 [US3] Confirm T020 (No-FR `Publication` entry removed) is the only source change needed; run `quickstart.md` §7 to verify zero "no fr" matches across `html/`, `dita/`, `source.csv`, and `mock_pptx.py`

**Checkpoint**: User Story 3 fully working. T039–T041 should pass.
The corpus and all derived artefacts are free of the "No FR" label.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final sweep — regression suite, idempotency check,
constitution-style determinism, performance sanity.

- [ ] T043 [P] Run the full `python -m unittest discover tests/` suite and confirm zero regressions against the baseline captured in T002 (SC-005)
- [ ] T044 [P] Run the web test suite (`npm test` or whatever `tests/web/` uses — confirm from existing CI config) and confirm zero regressions in the rewritten student-edition and instructor-edition specs
- [ ] T045 [P] Run `quickstart.md` §1 through §10 in order on a clean checkout; confirm every "Expect …" check matches; record total wall-clock time for the publish step and compare to the plan.md performance goal (≈ 50% over feature 003's two-edition wall time, ≈ 21 DITA-OT invocations for the 7-publication corpus)
- [ ] T046 Final cleanup pass on the four edited Python files (`extract_to_csv.py`, `generate_dita.py`, `publish_html.py`, `mock_pptx.py`): remove any leftover TODO comments added during implementation; verify no docstring still references the removed `write_trainee_ditaval` name or the two-edition layout
- [ ] T047 Commit and push the implementation in logically grouped commits (Phase 2 foundational, Phase 3/4/5 stories, Phase 6 polish) to branch `claude/zealous-tesla-lqGEa`; do NOT open a PR (per CLAUDE.md instructions, PRs only on explicit request)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No code dependencies — pre-implementation review only
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational completion
  - US1 (Week 3 substitution) is the MVP — implement first
  - US2 (author hand-edit) builds on US1's generator + publisher edits but adds no new ditamap shape
  - US3 (No-FR removal) is largely covered by T020 inside US1; US3's test phase is a verification + idempotency hardening pass
- **Polish (Phase 6)**: Depends on US1 + US2 + US3 being complete

### User Story Dependencies

- **US1**: Requires Phase 2 — the foundational seam (audience column wired, DITAVAL profiles emitted) is what US1 exercises end-to-end
- **US2**: Requires Phase 2 + can in principle run in parallel with US1, but T038 (the §10 walkthrough) needs the three-edition publisher from T024–T026 to be in place — keep US2 sequenced after US1's source changes
- **US3**: T020 lives inside US1's source-change list (the No-FR removal is a side-effect of the mock-corpus changes US1 needs). US3's verification (T039–T041) can run after US1 lands

### Within Each User Story

- Tests are written FIRST and asserted to FAIL before the source change makes them pass (TDD ordering carried over from features 001–003)
- Test-first tasks are marked [P] across user stories when they touch different test modules; within one test module they share a file and serialise
- Source-change tasks within one story usually touch one script each (extractor / generator / publisher / mock-corpus) and can run in parallel up to the regen step (T027 / T028) which must serialise

### Parallel Opportunities

- **Phase 2 tests** (T003–T006) all touch different files → fully parallel
- **Phase 2 source** (T007–T011) touch four distinct scripts → fully parallel (then T010 serialises after T009 inside `generate_dita.py`)
- **US1 test-first** (T012, T014–T019) — six test extensions across `tests/test_mock_pptx.py`, `tests/test_generate_dita.py`, `tests/test_publish_html.py`, `tests/web/student-edition.test.js`, `tests/web/instructor-edition.test.js` → fully parallel (different files)
- **US1 source** (T020–T026) — five different files, parallel up to T027 / T028 which depend on every prior step
- **US2 tests** (T031–T035) — all extend `tests/test_generate_dita.py`, share a file → serialise within the file but parallel with US1's polish
- **US3 tests** (T039–T041) — touch `tests/test_publish_html.py` (×2) and `tests/test_mock_pptx.py` → T039/T040 serialise on `tests/test_publish_html.py`, T041 parallel
- **Polish** (T043–T045) — independent run-and-assert steps, fully parallel

---

## Parallel Example: User Story 1 test-first

```bash
# All independent (different files) — kick off as one batch:
Task: "Extend tests/test_mock_pptx.py with test_week_3_carries_audience_markers"     # T012
Task: "Extend tests/test_generate_dita.py with topicref audience emission test"      # T014
Task: "Extend tests/test_generate_dita.py with empty-audience no-attribute test"     # T015
Task: "Rewrite tests/web/student-edition.test.js as own/other variants"              # T016
Task: "Update tests/web/instructor-edition.test.js URL-parity to two-pass form"      # T017
Task: "Extend tests/test_publish_html.py with three-edition layout test"             # T018
Task: "Extend tests/test_publish_html.py with Week 3 substitution count test"        # T019
```

(T014 / T015 share `tests/test_generate_dita.py` and T018 / T019
share `tests/test_publish_html.py` — those pairs serialise on
file ownership but the four pairs run in parallel with each other.)

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T011) — CSV column wired, DITAVAL profiles emitted
3. Complete Phase 3: User Story 1 (T012–T030) — Week 3 substitution end-to-end
4. **STOP and VALIDATE**: run `quickstart.md` §6 and confirm SC-001
5. Demo / hand off MVP to the user for sign-off before continuing

### Incremental Delivery

1. Setup + Foundational → seam in place but no behaviour change
2. + US1 → MVP, Week 3 substitution shippable (deploy / demo)
3. + US2 → author hand-edit affordance works (demo on a chosen gram)
4. + US3 → No-FR publication fully gone (verify via grep)
5. + Polish → regression suite green, idempotency confirmed,
   performance pinned

### Parallel Team Strategy

With multiple developers:

1. Phase 1 + Phase 2 done collaboratively (one developer per script — extractor, generator, publisher, mock)
2. Once Phase 2 lands:
   - Developer A: US1 test-first → US1 source → US1 regen + verify
   - Developer B: US2 test-first (the consistency-check, vocabulary-gate, and double-tag assertions sit in `tests/test_generate_dita.py` and depend only on T022 / T036 / T037 from US1)
   - Developer C: US3 test-first + verification (touches only `tests/test_publish_html.py` and `tests/test_mock_pptx.py`)
3. Polish phase done collaboratively

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to its user story for traceability
- Test-first ordering inside each story: extend the test module
  with an assertion that captures the new behaviour, run the
  module to confirm the assertion fails, then make the source
  change, then re-run to confirm it passes
- The regen tasks (T027 / T028) are inputs to subsequent
  verification steps — `source.csv` and `dita/` are committed
  artefacts in this repo
- Idempotency (FR-014 / SC-004) is asserted in T040; do NOT
  introduce timestamp-bearing chrome anywhere; the publisher's
  existing `prettify_tree()` + `SOURCE_DATE_EPOCH` machinery is
  unchanged by this feature
- Do NOT open a PR (per `CLAUDE.md` instructions). Commit and push
  to `claude/zealous-tesla-lqGEa` per the task-description's
  branch contract; the user opens the PR explicitly when ready

# Feature Specification: Per-Gram Audience Tags via CSV `audience` Column

**Feature Branch**: `claude/zealous-tesla-lqGEa`
**Created**: 2026-05-22
**Status**: Draft
**Input**: User description: "For the week 3 tests, we need to handle a student who cannot see some test items. We have to hide one gram from him, but provide him with another — so he is still tested on the same number of grams. We're going to use audience attributes to do this, again choosing to use an 'exclude' filter. The filter will be `-own` for 'own nation can't see this' and `-other` for 'other nation can't see this'. This audience tag will be applied to the whole gram element in the week-3 index page. But we'll allow the model to be re-used so that steadily the author can add `-other` to other grams across the whole corpus. This avoids us having twin versions of the week 3 dataset. We'll drop the `Instructor Progress Test 3 Grams No FR` folder completely. The week 3 PPTX has been modified so that on the second grams slide the last two items have gained `[-own]` and `[-other]` tags. These should travel with the gram name through the CSV stage, but be extracted and applied as audience properties in the write-DITA stage." (refined: tags become a dedicated `audience` column on the CSV so the author can broaden the tagging across the whole corpus by editing one cell.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A student of one nation sees a test whose excluded gram has been silently substituted (Priority: P1)

A trainee from one nation ("own") opens the published Week 3 progress
test. The index page lists the same number of grams every other student
sees, but one of the grams in the listing is different: the gram that
would have revealed information classified for that student's
nation has been filtered out and a substitute gram (one that the
other-nation student cannot see) takes its place in the visible
sequence. The trainee works through the test without any indication
that other students see a different specific gram — the gram count,
numbering style, and surrounding chrome are identical to every other
edition.

**Why this priority**: This is the deliverable. Today the only way to
hide a single gram from one nation's trainees is to ship a duplicate
copy of the whole dataset (`Instructor Progress Test 3 Grams No FR`).
That duplication scales badly the moment more grams need per-nation
gating, and it forces the source corpus to carry redundant content.
Per-gram audience tags collapse the duplication into a single source
that publishes correctly for every audience.

**Independent Test**: Generate the corpus from the modified Week 3
PPTX, run the publish pipeline, and confirm that:
(a) the own-nation Week 3 test index page omits the gram tagged `-own`
in the source and includes every other gram (including the one tagged
`-other`);
(b) the other-nation Week 3 test index page omits the gram tagged
`-other` and includes every other gram (including the one tagged
`-own`);
(c) both editions list the same total number of grams as each other,
and the difference between the two indexes is exactly the two tagged
grams swapped in/out.

**Acceptance Scenarios**:

1. **Given** a Week 3 ditamap where the last two grams of the second
   slide are tagged `-own` and `-other` respectively, **When** the
   pipeline publishes the own-nation student edition, **Then** the
   Week 3 index page in that edition lists every gram from the source
   *except* the one tagged `-own`, and lists the gram tagged `-other`
   in its place in the visible sequence.
2. **Given** the same Week 3 source, **When** the pipeline publishes
   the other-nation student edition, **Then** the Week 3 index page in
   that edition lists every gram *except* the one tagged `-other`, and
   lists the gram tagged `-own` in its place.
3. **Given** both editions side-by-side, **When** a reviewer counts
   grams listed on the Week 3 index page in each, **Then** the two
   counts are equal — neither nation's student sees a shorter test.

---

### User Story 2 — The author can broaden audience tagging across the corpus by editing one CSV cell per gram (Priority: P1)

The course author needs to mark additional grams across other weeks
and progress tests as out-of-bounds for the other-nation audience,
without re-editing every PPTX. They open `source.csv`, find the row(s)
for the gram, and set the `audience` cell to `-other` (or `-own`, or a
space-separated combination). They re-run `generate_dita.py` and
`publish_html.py`. The newly tagged gram is filtered out of the
relevant student edition's index page, and the unchanged editions are
unaffected.

**Why this priority**: The whole point of moving the audience tag into
a dedicated CSV column (rather than leaving it embedded in the PPTX
text) is to let the author scale the tagging across the corpus without
touching twelve PowerPoint files. This story is what makes the model
re-usable.

**Independent Test**: Pick an arbitrary gram that the source PPTX did
*not* tag, edit its `audience` cell in `source.csv` to `-other`,
re-run the DITA-generate + publish steps, and confirm the gram
disappears from the other-nation student edition's index page while
remaining visible in the own-nation and instructor editions.

**Acceptance Scenarios**:

1. **Given** a row in `source.csv` whose `audience` cell is empty,
   **When** the author edits the cell to `-other` and re-runs the
   pipeline from `generate_dita.py` onward, **Then** the corresponding
   gram is omitted from every page of the other-nation student
   edition's index/listing and remains present in the instructor and
   own-nation editions.
2. **Given** a row with `audience` set to `-own -other`, **When** the
   pipeline runs, **Then** the corresponding gram is omitted from
   *both* student editions and remains present only in the instructor
   edition.
3. **Given** a CSV with no `audience` values set on any row, **When**
   the pipeline runs, **Then** every gram appears in every edition
   (the audience column defaults to "show to all" when empty).

---

### User Story 3 — The duplicate "No FR" publication is removed, eliminating a maintenance liability (Priority: P2)

The corpus today carries two parallel copies of Progress Test 3:
`Instructor Progress Test 3 Grams` and `Instructor Progress Test 3
Grams No FR`. The "No FR" copy exists solely so one nation's trainees
do not see the `FR ` prefix on vessel descriptors that are off-limits
to them. With per-gram audience tags in place, the duplicate copy
becomes obsolete: a single Progress Test 3 dataset can serve every
audience. The duplicate publication is removed from the mock corpus
generator, from `source.csv`, and from the published output.

**Why this priority**: This is the proof that the audience-tag model
actually replaces the duplication strategy. Without it, the new model
is layered *on top of* the existing duplication rather than
*replacing* it.

**Independent Test**: After running the pipeline end-to-end, confirm
that no folder, ditamap, HTML page, or CSV row references the string
"Progress Test 3 Grams No FR" (case-insensitive).

**Acceptance Scenarios**:

1. **Given** the regenerated mock corpus, **When** a reviewer lists
   the publications in `mock_pptx_data/`, **Then** there is no
   `Instructor Progress Test 3 Grams No FR.pptx` or sibling files
   directory.
2. **Given** the regenerated `source.csv`, **When** a reviewer greps
   the file for "no fr" (case-insensitive), **Then** zero rows match.
3. **Given** the published HTML output, **When** a reviewer walks the
   `html/` tree, **Then** no folder, page title, or link label
   references "No FR" in any edition.

---

### Edge Cases

- A gram descriptor in the PPTX ends with `[xxx]` where `xxx` is not a
  recognised audience token (e.g. `[note]`, `[draft]`). The extractor
  MUST still strip the bracketed suffix into the `audience` column
  verbatim; validation of audience-token vocabulary is the DITA
  generator's job, not the extractor's. The DITA generator MUST warn
  (not fail) when it encounters an unrecognised audience token and
  MUST emit the `audience=` attribute verbatim — DITA-OT's DITAVAL
  filter ignores tokens that no profile names, so an unknown token
  is a no-op in publication.
- A gram descriptor ends with `[-own] [-other]` (two adjacent
  bracketed groups). The extractor MUST treat each bracketed group as
  a separate token and join them with a single space inside the
  `audience` cell (`-own -other`). The DITA generator MUST then split
  on whitespace and emit `audience="-own -other"` on the topicref.
- The `audience` cell carries leading/trailing whitespace or repeated
  spaces (a human just edited the cell). The DITA generator MUST
  normalise whitespace to single spaces and trim before emitting the
  attribute, so re-runs over a human-edited CSV are byte-identical to
  re-runs over a freshly-extracted CSV.
- A gram has an `audience` value set on the analysis row but a
  different value (or empty) on its GLC rows (or vice-versa) within
  the same `(publication, chapter, gram_id)` group. The DITA generator
  MUST treat this as an authoring error and fail fast with a clear
  message naming the offending gram — the audience tag is a
  per-gram property and inconsistency between rows of the same gram
  must not silently resolve to "one of them wins."
- The `audience` cell contains a non-exclude token (e.g. `own`
  without the leading `-`). Per the project's existing convention
  (feature 003: `-trainee` is the established exclude token), an
  audience value with no leading `-` would be an *include* filter
  rather than an exclude filter. This feature publishes only exclude
  filters; an include-style value MUST be flagged by the DITA
  generator as an authoring error.
- A gram tagged `-own` and a gram tagged `-other` appear adjacent on
  the same index page. After audience filtering, the *visible*
  sequence in each student edition closes up — there is no blank gap,
  no stray separator, no "Gram 7" → "Gram 9" jump where a reader can
  infer a gram was hidden. The relative ordering of the surviving
  grams is preserved exactly as in the CSV.
- A second publish run over an unchanged CSV produces byte-identical
  output in every edition (idempotency parity with features 001 / 003).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CSV schema MUST gain a new column named `audience`,
  appended to the existing column order so older CSVs upgrade
  forward-compatibly (a CSV without the column is read as if every
  row had an empty `audience` value).
- **FR-002**: The PPTX extractor (`extract_to_csv.py`) MUST detect a
  trailing bracketed group `[xxx]` on the gram-descriptor text (i.e.
  on the portion right of the `Gram N:` colon), strip the bracket
  pair and its contents from the descriptor, and write the inside
  text into the `audience` column for every CSV row that belongs to
  that gram.
- **FR-003**: Multiple adjacent bracketed groups on the same
  descriptor (e.g. `[-own][-other]` or `[-own] [-other]`) MUST be
  concatenated into a single whitespace-separated value inside the
  `audience` cell.
- **FR-004**: All CSV rows that share a single
  `(publication, chapter, gram_id)` key MUST receive the same
  `audience` value when written by the extractor. The DITA generator
  MUST fail fast if it later reads back rows of the same gram with
  conflicting `audience` values.
- **FR-005**: The DITA generator (`generate_dita.py`) MUST emit each
  per-gram `audience` value as an `audience="…"` attribute on the
  `<topicref>` element that links the gram from its parent ditamap
  (the per-publication index for `progress-test-N` publications; the
  per-chapter `<topichead>` for `main`). The attribute MUST be
  omitted when the value is empty.
- **FR-006**: The DITA generator MUST NOT propagate the per-gram
  `audience` value onto the gram's `<topic>` element or onto any
  element inside the topic. The whole-gram exclusion is achieved by
  filtering the topicref out of the index — the topic file itself is
  audience-neutral so that a reader who reaches it via a direct URL
  sees the full content.
- **FR-007**: The publish step (`publish_html.py`) MUST replace the
  current single `html/student/` edition with two nation-specific
  student editions: `html/student-own/` (DITAVAL excludes `-trainee`
  *and* `-own`) and `html/student-other/` (DITAVAL excludes
  `-trainee` *and* `-other`). The instructor edition
  (`html/instructor/`) remains unfiltered.
- **FR-008**: The shared landing page at `html/index.html` MUST list
  three editions — instructor, own-nation student, other-nation
  student — replacing the two-edition landing produced by feature
  003. Each entry MUST carry a short human-readable description of
  the intended audience so a reviewer at the landing page can tell
  the three apart without clicking through.
- **FR-009**: The `Instructor Progress Test 3 Grams No FR`
  publication MUST be removed from the mock corpus generator
  (`mock_pptx.py`) and from any regenerated `source.csv`. The
  `no_fr` Publication-spec flag and the conditional `"FR "` prefix
  logic in `_pick_descriptor` MAY be retained (they are independent
  authoring affordances) but MUST NOT instantiate any publication.
- **FR-010**: The mock corpus generator MUST plant `[-own]` and
  `[-other]` audience tags on representative grams of at least one
  publication so the end-to-end pipeline exercises every code path
  under test. The exact grams chosen MUST be deterministic for a
  fixed seed (consistent with the existing mock-data determinism
  guarantee).
- **FR-011**: For every gram whose `audience` cell contains both
  `-own` and `-other` (in either order), the gram MUST appear in the
  instructor edition only — both student editions MUST filter it out.
- **FR-012**: For every gram whose `audience` cell is empty, the
  gram MUST appear in every edition (instructor, student-own,
  student-other). Empty audience MUST behave identically to a missing
  `audience` column.
- **FR-013**: Both student editions of every publication MUST list
  the same *number* of grams as each other on every index/listing
  page, whenever the source CSV pairs each `-own`-tagged gram with
  an `-other`-tagged sibling gram. (When the pairing is not balanced
  in the source, the editions naturally differ in count — this is a
  reportable property of the authored content, not a publish bug.)
- **FR-014**: Re-running the pipeline over an unchanged
  `source.csv` MUST produce byte-identical HTML output in all three
  editions (idempotency parity with features 001 and 003).
- **FR-015**: The DITA generator MUST log, per publication, how many
  topicrefs received an `audience=` attribute and what tokens were
  applied, so a reviewer reading the build log can confirm that the
  expected number of grams was tagged.
- **FR-016**: The pipeline MUST tolerate, without erroring, an
  `audience` cell whose token is not recognised by any of the three
  current DITAVAL profiles. The generator emits the attribute
  verbatim; DITA-OT silently ignores unknown audience tokens, so the
  gram appears in every edition (the safe default). The generator
  MUST log a warning naming the unknown token so the author notices.
- **FR-017**: The change MUST NOT regress any signed-off behaviour
  from features 001, 002, or 003. The audience-tagging machinery
  introduced by feature 003 for `-trainee` (vessel-name redaction,
  Analysis Sheet redaction, chapter-navtitle "Instructor " prefix,
  map-title "Instructor Version" suffix) MUST continue to operate
  unchanged.

### Key Entities

- **Audience token**: A single hyphen-prefixed identifier (e.g.
  `-own`, `-other`, `-trainee`) naming an exclude condition. Tokens
  are case-sensitive lowercase. A gram may carry zero, one, or many
  tokens; multiple tokens are space-separated inside one `audience`
  attribute.
- **Per-gram audience value**: The contents of the `audience` cell
  for the rows of a single `(publication, chapter, gram_id)` group.
  Travels through the pipeline as a CSV cell, lands in the DITA tree
  as an `audience="…"` attribute on the gram's topicref.
- **Edition**: A complete HTML rendering produced by one DITAVAL
  profile. Feature 003 defined two (instructor, student); this
  feature redefines the family as three: *instructor* (no filter),
  *student-own* (excludes `-trainee -own`), *student-other*
  (excludes `-trainee -other`).
- **Topicref**: The DITA element in a ditamap that links a topic
  file into an index/listing. The new `audience` attribute lives on
  the topicref, not on the topic. This is what gives each student
  edition a *shorter* index page rather than a *gapped* topic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the modified Week 3 PPTX is processed end-to-end,
  the own-nation student edition's Week 3 test index page omits
  exactly one gram (the one tagged `-own` in the source) and
  includes the gram tagged `-other`, and the other-nation student
  edition's Week 3 test index page omits exactly one gram (the one
  tagged `-other`) and includes the gram tagged `-own`. Both
  editions' Week 3 index pages list the *same number* of grams as
  each other.
- **SC-002**: An author can hide one additional gram from the
  other-nation student edition by editing exactly one CSV cell
  (the `audience` cell of the gram's first row) and re-running the
  pipeline. No PPTX edits, no script edits, and no DITA edits are
  required.
- **SC-003**: After this feature ships, the substring "no fr"
  (case-insensitive) returns zero matches across the entire `dita/`
  tree, the entire `html/` tree, `source.csv`, and `mock_pptx.py`.
- **SC-004**: Two consecutive publish runs over an unchanged
  `source.csv` produce byte-identical HTML in all three editions.
- **SC-005**: The existing `unittest` suite (covering features 001,
  002, 003) continues to pass with zero regressions. New tests cover
  the CSV `audience` column round-trip, the topicref `audience`
  attribute emission, the dual-student-edition publish, and the
  removal of the `No FR` publication.
- **SC-006**: A reviewer arriving at `html/index.html` can reach the
  per-publication index of any of the three editions in one click
  and can tell which edition is in view from the URL alone (the URL
  path begins with `instructor/`, `student-own/`, or `student-other/`).
- **SC-007**: The pipeline raises a clear, named error when an
  author commits a CSV in which two rows of the same gram disagree
  on their `audience` value — the author sees which gram is at
  fault without grepping the build log.

## Assumptions

- The PPTX descriptor convention extends feature 001's `"Gram N:
  <vessel detail>"` shape to allow an optional trailing bracketed
  group on the right-hand side: `"Gram N: <vessel detail> [-own]"`,
  `"Gram N: <vessel detail> [-other]"`, or
  `"Gram N: <vessel detail> [-own][-other]"`. The bracketed group is
  the only thing the extractor strips from the descriptor before
  computing `vessel_name`; everything else about the descriptor
  format (the colon, the `Gram N` prefix, the fielded-vs-sentence
  vessel-detail format) is unchanged from feature 001's
  csv-schema.md.
- Audience tokens live in the *right* side of the descriptor (after
  the colon), not the left side. This keeps `gram_id` a clean
  integer (preserving the refactoring affordance from feature 001's
  csv-schema.md §3) and means a gram with no vessel name but an
  audience tag is authored as `"Gram 7: [-other]"` — i.e. a colon
  with an audience-only right side.
- The `audience` CSV column is appended *after* the existing
  `warnings` column at the right edge of the CSV, so the column
  order documented in
  `specs/001-pptx-dita-migration/contracts/csv-schema.md` for the
  existing 16 columns is preserved unchanged. A 16-column CSV reads
  back as if every row had an empty 17th `audience` cell. (Feature
  004 also drops the stale `analysis_docx_path` row from
  csv-schema.md — the row was documented but never matched the
  actual extractor output; after main's unrelated `file_size`
  addition the doc and code agree at 16 real columns once the stale
  row is removed.)
- The author edits `source.csv` directly when broadening audience
  tagging across the corpus. The `audience` column is the *one*
  cell the author is encouraged to hand-edit; the other cells remain
  authored upstream in the PPTX and re-derived by the extractor.
- The DITAVAL profiles for the three editions are emitted by
  `generate_dita.py` into the dita staging tree (per feature 003's
  pattern for `trainee.ditaval`, which is also generator-emitted).
  Feature 003's `trainee.ditaval` is now joined by two new
  profiles emitted alongside it: one excluding `-trainee -own`,
  one excluding `-trainee -other`. The instructor edition uses no
  DITAVAL profile.
- Audience-token vocabulary remains small and exclude-only. This
  feature introduces exactly two new tokens (`-own`, `-other`) on
  top of feature 003's `-trainee`. A larger taxonomy (per-cohort
  filters, per-publication audience overrides, include filters) is
  out of scope.
- The DITA generator emits the `audience` attribute on the
  *topicref* (not on the topic file's root element) because the
  user's requirement is that the *index page* hides the gram, not
  that the gram becomes 404 for the excluded audience. A reader who
  navigates to the gram via a direct URL — bypassing the index —
  will see the gram in any edition. This is acceptable because
  there is no other navigation surface today that would expose the
  gram outside the index page.
- Within a single gram, the `audience` value is a property of the
  whole gram. The DITA generator reads it from the first row of the
  gram group and asserts consistency on the remaining rows; the
  attribute is emitted exactly once, on the topicref.
- The "FR " / "no FR " distinction historically encoded in the
  `Instructor Progress Test 3 Grams No FR` publication is fully
  subsumed by the per-gram audience model — the dropped publication
  carried no content unique from the kept one beyond the `FR `
  prefix on vessel descriptors, and vessel descriptors are already
  audience-tagged `-trainee` by feature 003 and so never reach a
  student edition regardless.

## Out of Scope

- No change to the source-CSV sign-off workflow itself (the author
  reviews and approves `source.csv` exactly as before; this feature
  only adds one column to what the author may edit).
- No introduction of include-style audience filters. The DITAVAL
  profiles remain exclude-only.
- No change to the spectrogram-table contract, the analysis-sheet
  redaction (feature 003), or the instructor/student layout split
  (feature 003) beyond replacing the single student edition with
  two nation variants.
- No support for per-publication audience overrides (e.g. "treat
  `-own` as `-other` for Pub10 only"). One CSV cell, one universal
  effect.
- No runtime audience-switching UI. Each edition is a separate
  static HTML tree under `html/`, distributable independently.
- No re-tagging of grams in the existing `source.csv` beyond what
  flows automatically from the modified Week 3 PPTX. Broadening the
  tag coverage across the rest of the corpus is the author's
  ongoing task, not a deliverable of this feature.

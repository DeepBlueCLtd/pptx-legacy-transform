# Specification Quality Checklist: Analysis-Sheet Word Originals

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-07
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

**Validation iteration 1 — findings and resolutions**

1. *No implementation details*: An earlier draft named the specific scripts,
   functions, and the exact CSV column (`analysis_doc_path`). Resolved — FR-005
   now states the requirement as "recorded in the intermediate CSV so the
   generator consumes it from the CSV rather than re-deriving it from the source
   tree", leaving the column name to `/speckit-plan`. Filenames that form part of
   the *observable contract* (`analysis.png` → `analysis.doc`/`.docx`) are
   retained deliberately: they are the output an analyst sees, not an internal
   choice.

2. *Testable requirements*: "Remove the step" was ambiguous between deleting the
   behaviour and defaulting its flag off. Resolved — FR-010 states the removal is
   outright and adds the verifiable condition that no option can re-enable it,
   with US2 acceptance scenario 3 testing exactly that.

3. *Technology-agnostic success criteria*: SC-003 originally referred to the
   `html/` tree and its three named editions. Reworded to "the published output
   for every edition".

4. *Scope boundedness*: added the **Dependencies** section recording that US2
   must reach the delivered corpus with or before US1, since that ordering is a
   correctness constraint rather than a preference.

**Deliberate deviations from the template**

- An **Overview** section precedes the user stories, matching the house style of
  specs 011 and 012. It carries the reasoning for the removal half of the
  feature, which is otherwise hard to justify from requirements alone.
- No [NEEDS CLARIFICATION] markers were raised. The three candidates — whether
  the document should also reach the published HTML, whether the sweep is a new
  script or an extension of an existing one, and the CSV column's name — were
  resolved as a documented assumption, a deferral to planning (constitution
  Principle II prefers extending an existing stage), and a deferral to planning
  respectively.

**Resolved during implementation**

The four questions left open above were decided as follows:

- **Where the sweep lives** — `snapshot_analysis_docs.py --sweep-wrappers`,
  per Principle II. It also keeps the wrapper's content signature in the same
  file whose history produced it. `--apply` opts into deletion.
- **The CSV column** — `analysis_doc_path`, appended at the right edge of
  `CSV_COLUMNS`, and added to the generator's `OPTIONAL_CSV_COLUMNS` so a CSV
  written before this feature reads forward-compatibly.
- **Mock corpus fixtures** — no change needed. `mock_pptx._emit_analysis_sheet`
  already emits all three shapes: `.doc` + rendered `.png`, `.docx` alone, and
  a PNG-only `Analysis.png`. The third gives the no-original path its fixture.
- **The committed wrappers** — swept in the implementing PR. 202 fabricated
  `Analysis.docx` files were found and deleted; the 173 genuine
  `Analysis Sheet.docx` documents were untouched, and a re-run reported zero.

**Verified end-to-end against the mock corpus**

- Extraction reports `analysis_sheets=375 without_word_original=202` — the 202
  matching the swept fakes exactly. Before the sweep all 375 would have claimed
  an original, which is the signal corruption FR-010/FR-011 exist to stop.
- After `dedupe` → `write`, all **173** genuine Word originals reach the DITA
  tree (SC-001). Running `write` on an *un-deduped* CSV lands 161: five topics
  are two colliding grams merged into one, where the surviving row's sheet is
  image-only. That is the pre-existing within-week collision the dedupe step
  exists to fix (the analysis *image* was already chosen the same way), and
  the documented pipeline order resolves it.
- Two consecutive generator runs produced byte- and mtime-identical trees
  (SC-007), copied Word documents included.

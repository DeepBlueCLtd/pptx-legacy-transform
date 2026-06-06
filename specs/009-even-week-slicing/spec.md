# Feature Specification: Even-slice no-week `main` decks across the four weeks

**Feature Branch**: `009-even-week-slicing`
**Created**: 2026-06-06
**Status**: Draft
**Input**: User description: "Stakeholders couldn't agree which week each Pub10 / Legacy Pub10 gram belongs to, so slice them evenly across the four weeks. Drop the extra source-document folder tier under `main`. Renumber the resulting duplicate gram numbers in a later stage."

> **Numbering scheme is a supported toggle, not a blocker.** `main` can be
> numbered two ways — a single **continuous** sequence across the four weeks, or
> each week **restarting at 1** — and this feature **supports both**, selected by
> a parameter on the renumbering step (FR-009, FR-012). The document author will
> choose which becomes the default (expected within a few days); until then the
> provisional default is the continuous scheme. Because the toggle is confined to
> the renumber step and the rest of the pipeline is scheme-agnostic, the author's
> later decision does not reopen the design — so this spec is complete and can be
> reviewed and merged now.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - No-week decks publish into the four weeks with no manual table (Priority: P1)

The corpus contains decks that carry a `Week N` token in their folder title
(assigned to that week) and decks that do not — notably **Pub10** and a separate
**Legacy Pub 10**. The week destination for the no-week decks was meant to come
from a stakeholder-agreed table, but the stakeholders cannot agree. The technical
author runs the pipeline and the no-week decks' grams are **distributed evenly
across the four weeks** of `main` automatically, with no per-gram table to fill
in, and the publication builds with no number collisions.

**Why this priority**: This is the whole point of the feature — it unblocks
publishing `main` despite the missing stakeholder decision. Without it the
no-week decks have nowhere to go.

**Independent Test**: Run the pipeline (extract → dedupe → generate) on a corpus
containing one no-week `main` deck of known size; confirm its grams appear spread
across `week-1`…`week-4` with counts differing by at most one, and that the build
produces no duplicate gram folders.

**Acceptance Scenarios**:

1. **Given** a no-week `main` deck with 12 grams, **When** the pipeline runs,
   **Then** 3 grams land in each of the four weeks, in source order.
2. **Given** a no-week `main` deck with 10 grams, **When** the pipeline runs,
   **Then** weeks 1–2 receive 3 grams each and weeks 3–4 receive 2 each.
3. **Given** "Legacy Pub 10" (also no-week), **When** the pipeline runs, **Then**
   it is sliced the same way as Pub10 with no special-case handling.
4. **Given** a deck whose folder title carries `Week 2`, **When** the pipeline
   runs, **Then** all its grams land in week 2 (it is NOT sliced).

---

### User Story 2 - `main` reads as flat week folders (Priority: P2)

When `main` is published, each gram sits directly under its week folder
(`main/week-N/gram-NN/`) with **no source-document folder tier** in between.
A reader navigating an edition sees week → gram, not week → source-document →
gram.

**Why this priority**: The extra per-document tier is unwanted chrome in the
delivered output. Removing it is independently observable and valuable, and it is
the change that forces publication-wide numbering (Story 3).

**Independent Test**: Generate the DITA tree for a `main` corpus and confirm no
folder level exists between `week-N` and `gram-NN` for any gram.

**Acceptance Scenarios**:

1. **Given** a gram from the Pub10 deck assigned to week 1, **When** the tree is
   generated, **Then** it is written at `main/week-1/gram-NN/` (no `pub10…/`
   segment).
2. **Given** two different source decks both contributing grams to week 1,
   **When** the tree is generated, **Then** both decks' grams share the single
   `main/week-1/` folder with no per-deck subfolders.

---

### User Story 3 - Every `main` gram has a unique, traceable number (Priority: P2)

Even-slicing makes several decks contribute to the same week, so raw gram numbers
collide. The pipeline reassigns numbers so that **every gram in `main` has a
unique number**, recording the new number without destroying the original, so an
author can still trace a gram back to its source.

**Why this priority**: With the flat layout (Story 2) a number collision is a
folder collision — it must be resolved or the build fails. Traceability matters
because grams are referenced by number in instruction.

**Independent Test**: Run dedupe on a sliced corpus; confirm no two `main` grams
share an effective number, and that each reassigned row preserves its original
source number alongside the new one.

**Acceptance Scenarios**:

1. **Given** week 1 already has a native gram numbered 5 and a sliced-in Pub10
   gram also numbered 5, **When** dedupe runs, **Then** the two grams receive
   distinct effective numbers and the original source numbers are still present.
2. **Given** a renumbered gram, **When** the tree is generated, **Then** the
   folder, topic filename, topic id and title all use the new effective number.
3. **Given** the same sliced corpus, **When** the renumber runs once per scheme
   (continuous vs per-week), **Then** each run produces folder-unique output and
   the only difference between the two is the assigned numbers — the week
   assignments and folder layout are identical.

---

### Edge Cases

- **Fewer grams than weeks (G < 4):** a deck with 3 grams puts one gram each in
  weeks 1–3 and none in week 4 (no empty `gram-` folders, no crash).
- **G not divisible by 4:** the remainder goes to the earliest weeks (10 →
  3/3/2/2), deterministically.
- **Multiple no-week decks:** their per-week grams accumulate; numbering stays
  unique across the whole publication.
- **A genuinely duplicated authoring row** (same gram on every identity field)
  is still a real error and must fail fast, distinct from the legitimate
  many-decks-share-a-week case the renumber resolves.
- **Residual un-renumbered collision** (dedupe not run, or a number still clashes)
  must fail the build with a message that names the dedupe step, not silently
  emit a colliding folder.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Publication classification MUST be unchanged. Decks matching the
  existing progress-test rule and the configured final-assessment pattern still
  route to their own publications; only decks that route to `main` **and** carry
  no `Week N` folder token are affected by this feature.
- **FR-002**: For a no-week `main` deck with G grams, the system MUST distribute
  the grams across the four weeks as `floor(G/4)` per week with the `G mod 4`
  remainder assigned to the earliest weeks, preserving source order (the first
  slice → week 1, the next → week 2, and so on).
- **FR-003**: The week assignment for each affected gram MUST be recorded in the
  editable `target_chapter` column during extraction, replacing the previous
  "leave blank for an analyst" behaviour for no-week `main` decks. Decks with a
  `Week N` token keep their existing single-week assignment.
- **FR-004**: Generated `main` grams MUST be laid out at `main/week-N/gram-NN/`
  with no source-document folder tier between the week and the gram. Non-`main`
  publications MUST be unaffected.
- **FR-005**: No two `main` grams may resolve to the same output folder
  (`main/week-N/gram-NN/`). The collision key MUST drop the source-document
  dimension for `main` (a consequence of FR-004's flat layout), enforcing
  uniqueness on `(publication, week, effective number)`. This holds under either
  numbering scheme (FR-009): continuous numbering is unique publication-wide;
  per-week numbering is unique within each week, which the week path segment keeps
  folder-unique.
- **FR-006**: Number reassignment MUST be recorded in the additive
  `target_gram_id` column; the original `gram_id` MUST never be mutated; and all
  generated names (folder, topic filename, topic id, title) MUST derive from the
  effective number (`target_gram_id` when set, else `gram_id`).
- **FR-007**: Extraction MUST NOT be required to resolve number collisions; it
  may emit colliding raw numbers and defer resolution to the renumbering step.
- **FR-008**: A residual collision that survives renumbering MUST cause the
  generator to fail fast with an operator-facing message that points to the
  renumbering step.
- **FR-009**: The renumbering step MUST support two `main` numbering schemes,
  selectable per run:
  - **continuous** (provisional default): one sequence across the four weeks,
    ordered by (week, then within-week source order); week N begins at one past
    week N-1's maximum, so inserting grams into an earlier week shifts the
    starting number of later weeks (e.g. week 2 starts at 35 once 10 grams land
    in week 1).
  - **per-week**: each week is numbered independently from 1.

  Both schemes MUST yield folder-unique output per FR-005.
- **FR-010**: The slicing and the renumbering MUST be deterministic — the same
  signed-off CSV MUST produce byte-identical week assignments, number
  assignments, and generated output on every run (no wall-clock or
  ordering-sensitive-to-iteration behaviour).
- **FR-011**: "Legacy Pub 10" MUST be handled by the same no-week slicing path as
  Pub10, with no document-specific special case.
- **FR-012**: The numbering scheme MUST be selected by a single parameter on the
  renumbering step (a flag on `deduplicate_csv.py`); no other stage needs to know
  the scheme. Extraction (slicing) and generation (flat layout + folder-uniqueness
  check) MUST behave identically regardless of the chosen scheme. The default
  scheme is provisional (continuous), and changing the default MUST be a one-line
  change.

### Key Entities *(include if feature involves data)*

- **No-week `main` deck**: a source document that routes to `main` and lacks a
  `Week N` folder token (e.g. Pub10, Legacy Pub 10). The subject of slicing.
- **Week assignment** (`target_chapter`): which of the four weeks a gram lands in;
  set automatically by the even slice for no-week decks.
- **Effective gram number** (`target_gram_id` or `gram_id`): the number that
  drives every generated name; reassigned for collisions, with the source number
  preserved.
- **`main` numbering space**: the set of effective numbers across all four weeks,
  required to be collision-free for the whole publication.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A no-week deck of any size publishes with every one of its grams in
  exactly one week, and per-week counts differing by at most one.
- **SC-002**: A full-corpus `main` build has zero duplicate gram folders under
  either numbering scheme (no collision failures, no overwritten topics).
- **SC-003**: In the published `main` tree, the navigation depth from a week to a
  gram is exactly one level — there is no intermediate source-document folder.
- **SC-004**: Re-running the pipeline on an unchanged signed-off CSV yields
  byte-identical DITA output, including week assignments and gram numbers.
- **SC-005**: Publishing `main` requires zero manual per-gram week-assignment
  input (no stakeholder table, no analyst editing of `target_chapter` for the
  no-week decks).
- **SC-006**: For every renumbered gram, the original source gram number remains
  recoverable from the CSV.

## Assumptions

- The `Week N` token detection introduced for the four-week IA is the signal that
  distinguishes week-assigned decks from no-week decks; decks without it are the
  ones sliced.
- The number of weeks is fixed at four.
- Grams have a stable, meaningful source order within a deck (the order extraction
  already emits), which is the basis for both the even slice and the renumber.
- Even (count-based) distribution is acceptable to stakeholders as the interim
  answer in place of a content-aware assignment.
- The renumbering step becomes **effectively required** for any corpus that slices
  a no-week deck: without it the colliding numbers trip the generator's fail-fast
  (FR-008). (It remains inert/optional for corpora that do not slice.)
- "Even" is defined by gram **count**, not by duration, difficulty, or any
  content weighting.

## Deferred decisions (non-blocking)

- **Which numbering scheme is the default.** The feature supports *both* schemes
  (FR-009, FR-012); only the **default** — which scheme runs when the flag is
  omitted — is undecided, pending the document author (expected within a few
  days). The provisional default is **continuous**. Because the toggle is confined
  to the renumbering step and the rest of the pipeline is scheme-agnostic, this
  decision blocks neither review, merge, nor implementation: either answer is a
  one-line change to the default and reopens no part of the design.

## Out of Scope

- The abandoned stakeholder per-gram week-assignment table.
- Any change to how progress-test or final-assessment decks are classified or
  routed.
- Content-aware (non-even) distribution of grams across weeks.

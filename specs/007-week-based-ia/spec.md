# Feature Specification: Week-Based Information Architecture for `main`

**Feature Branch**: `claude/fervent-goldberg-9M4pc` (developed on the existing working branch; no separate feature branch)
**Created**: 2026-05-29
**Status**: Draft
**Input**: User description: "We've agreed a slightly different information architecture. Currently we slice the `main` publication according to the original input documents (~12 pages). Instead, within `main` we organise the data into 4 folders, one per week, so the target chapter is one of 1, 2, 3, 4 — expanded to `Week 1` … `Week 4`. As the CSV is extracted, a folder title containing `Week 1` puts `1` into the target chapter. Today, `Gram 1` in two separate folders kept unique id paths; we lose that under one shared week folder, so extend the dedupe step to renumber: for a target chapter, if a gram number is already taken, use one greater than the existing largest number for that chapter."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Collapse `main` into four week folders (Priority: P1)

A migration operator wants the `main` publication organised not by the dozen
original input decks but into exactly **four** chapters — one per teaching week.
Each gram in a `Week N` source deck should land under a `Week N` chapter in the
output, and Pub10 grams (which an analyst assigns to a week by hand) should
land in whichever week the analyst nominates. The visible chapter heading reads
`Week 1` … `Week 4`; the on-disk folder is `main/week-1/` … `main/week-4/`.

**Why this priority**: This is the headline change — it is the new
information architecture the stakeholder agreed and the thing the reader sees.

**Independent Test**: Extract the corpus; confirm every `Week N` deck's grams
carry target chapter `N`; set a Pub10 gram's target chapter to `2` by hand;
generate; confirm the gram is emitted under `main/week-2/` with the heading
`Week 2`, and that `main` contains only week chapters.

**Acceptance Scenarios**:

1. **Given** a source deck whose folder title contains `Week 3`, **When** the
   CSV is extracted, **Then** every row for that deck carries target chapter
   `3` (and the immutable source `chapter` keeps the full deck title).
2. **Given** a signed-off CSV in which a Pub10 gram's target chapter has been
   set to `2`, **When** the DITA is generated, **Then** that gram is emitted
   under `main/week-2/` alongside the native Week 2 grams, with no per-document
   sub-folder.
3. **Given** target chapter `1`, **When** the main ditamap and topic are
   generated, **Then** the chapter navtitle reads `Week 1` and the folder slug
   is `week-1`.

---

### User Story 2 - Renumber colliding grams within a week (Priority: P1)

Because several source decks now share one week folder, two grams that were
previously kept apart only by their separate chapter folders (e.g. a native
`Week 2 / Gram 5` and a Pub10 `Gram 5` reassigned to Week 2) would now collide
on the same `gram-05/` path. The operator wants the dedupe post-processing step
to **renumber** the colliding gram: within a target chapter, a gram whose
number is already taken is reassigned to one greater than the existing largest
number for that chapter, so every gram in the week gets a clean, unique number
and the generated DITA needs no letter-suffix disambiguation.

**Why this priority**: Without renumbering, collapsing decks into shared week
folders would either merge two distinct grams into one topic (data loss) or
fall back to noisy `gram-05a` / `gram-05b` folder names. Renumbering is what
makes the new architecture produce neat, unique paths.

**Independent Test**: Hand a CSV where two distinct grams resolve to `Gram 5`
in the same target week to the dedupe step; confirm the second (by the defined
order) is renumbered to one past the week's current maximum, recorded in a new
column, while the first keeps its number; generate and confirm two separate,
cleanly-numbered topics.

**Acceptance Scenarios**:

1. **Given** a week containing native grams 1–10 and a reassigned Pub10 gram
   that also claims number 5, **When** the dedupe step runs, **Then** the Pub10
   gram is renumbered to 11 (one past the current maximum) and the native gram
   keeps 5.
2. **Given** two distinct grams both claiming the same number in the same week,
   **When** the order is resolved, **Then** the deck whose source chapter sorts
   first alphabetically (then by CSV row order) keeps the original number and
   the later one is renumbered — deterministically.
3. **Given** a renumbered CSV, **When** the DITA is generated, **Then** each
   gram is emitted at a unique `gram-NN/` path with title `Gram NN` using the
   renumbered value, and no letter-suffixed folders appear.

---

### User Story 3 - Fail fast when a week still has a collision (Priority: P2)

If the operator forgets to run the renumbering step (or hand-edits introduce a
fresh collision), two distinct grams could still resolve to the same week +
number. The operator wants the generator to **stop with a clear error** naming
the colliding grams and telling them to renumber, rather than silently merging
the two grams into one topic.

**Why this priority**: This is the safety net that replaces the old letter-suffix
auto-disambiguation; it guarantees the new architecture never loses a gram.

**Independent Test**: Feed the generator a CSV with two distinct grams sharing a
week + number and no renumbering applied; confirm it aborts before emission with
an error per collision that mentions renumbering.

**Acceptance Scenarios**:

1. **Given** two distinct grams sharing target chapter + effective gram number,
   **When** the generator validates row identity, **Then** it reports one error
   per colliding slot, names the grams, and aborts before writing any topic.
2. **Given** the same grams after the dedupe renumbering step has run, **When**
   the generator runs, **Then** it succeeds and emits two distinct topics.

---

### Edge Cases

- **Deck title without a week token** (e.g. Pub10): extraction leaves the
  target chapter blank for the analyst to fill in; the generator will route the
  gram by whatever week number the analyst enters.
- **Final Assessment deck**: routed to its own standalone publication like the
  progress tests — it is never part of `main` and is unaffected by the week IA.
- **A gram number larger than the running maximum that is not yet taken**: it
  keeps its number (it does not collide), and it extends the week's maximum for
  any later renumbering.
- **A week with no collisions**: no row is renumbered; the renumber column stays
  empty and the output is identical to numbering straight from `gram_id`.
- **Re-running the dedupe step**: renumbering is recomputed from the original
  `gram_id` each run, so a second run over the same inputs yields a byte-identical
  CSV (idempotent), matching the large-asset dedup behaviour.
- **Bare-integer target chapter outside 1–4**: still expands to `Week N` for any
  positive integer; the architecture targets weeks 1–4 but the rule is general.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Extraction MUST derive the target chapter for a `main` deck from a
  `Week N` token in the deck's folder title, writing the bare integer `N` into
  the editable `target_chapter` column while leaving the immutable `chapter`
  column holding the full source title.
- **FR-002**: When a `main` deck's folder title contains no week token,
  extraction MUST leave `target_chapter` empty so an analyst can assign the week
  by hand (the Pub10 path).
- **FR-003**: For `main`, extraction MUST NOT introduce a per-document folder
  segment: all grams for a week land directly under that week's chapter folder.
- **FR-004**: The generator MUST expand a bare-integer effective chapter `N`
  into the navtitle `Week N` and the folder slug `week-N`.
- **FR-005**: A post-processing step MUST renumber grams so that, within each
  target chapter, every distinct gram has a unique number: a gram whose number
  is already taken is reassigned to one greater than the existing largest number
  for that chapter.
- **FR-006**: The renumbering order MUST be deterministic: distinct grams are
  processed by source `chapter` (alphabetical) then by CSV row order; the first
  claimant of a number keeps it, later claimants are reassigned.
- **FR-007**: The renumbered value MUST be written to a new, optional,
  right-edge `target_gram_id` column; the immutable `gram_id` MUST be left
  unchanged as provenance. An empty `target_gram_id` means "unchanged — use
  `gram_id`".
- **FR-008**: The generator MUST derive each gram's folder name, topic filename,
  topic id, and visible `Gram NN` title from the effective gram number
  (`target_gram_id` when present, otherwise `gram_id`).
- **FR-009**: The generator MUST group rows into one topic per
  `(publication, effective chapter, effective doc, effective gram number)` and
  MUST NOT use letter-suffix disambiguation for colliding gram numbers.
- **FR-010**: The generator MUST abort before emission, with one clear error per
  colliding slot that names the grams and instructs the operator to renumber,
  when two distinct grams resolve to the same `(publication, effective chapter,
  effective doc, effective gram number, topic_type, sequence)`.
- **FR-011**: A CSV with no `target_gram_id` column (or an all-empty one) MUST
  produce output as if numbering came straight from `gram_id` — the column is
  additive and inert by default.
- **FR-012**: Re-running the renumbering step over an unchanged CSV MUST yield a
  byte-identical CSV (idempotent), and the renumber step MUST preserve the CSV
  file contract (utf-8-sig, CRLF, QUOTE_MINIMAL).
- **FR-013**: The main ditamap MUST group topicrefs by the effective (week)
  chapter and reference each topic at its effective-numbered path, so the map
  and the on-disk tree agree.

### Key Entities *(include if feature involves data)*

- **Target chapter** (existing `target_chapter`): for `main`, now a bare integer
  `1`…`4` (a week). Set automatically from a `Week N` deck title or by an analyst
  for Pub10 grams. Empty falls back to the immutable source `chapter`.
- **Effective chapter**: `target_chapter` when non-empty, else `chapter`. A
  bare integer expands to `Week N` / `week-N` for display and slug.
- **Target gram number** (new, optional `target_gram_id`): the renumbered gram
  number assigned by the dedupe step to resolve a within-week collision. Empty
  means "use `gram_id`". `gram_id` itself is never mutated.
- **Distinct gram**: the unit of renumbering — rows sharing
  `(publication, source chapter, gram_id, vessel_name)`. All of a gram's rows
  receive the same renumbered value.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After extraction, 100% of `Week N` decks' rows carry
  `target_chapter = N`, and `main` resolves to at most four week chapters
  (plus any week an analyst assigns to Pub10 grams).
- **SC-002**: For a week into which a duplicate gram number is introduced, the
  generated tree contains two distinct, uniquely-numbered `gram-NN/` folders and
  zero letter-suffixed folders.
- **SC-003**: Given a within-week collision, the renumbering step reassigns the
  later gram (by the defined order) to one past the week's current maximum, and
  the earlier gram keeps its number — verified deterministically.
- **SC-004**: A CSV with no `target_gram_id` column produces output identical to
  numbering straight from `gram_id` (no regression).
- **SC-005**: Re-running the renumbering step over an unchanged CSV produces a
  byte-identical CSV (idempotent).
- **SC-006**: A CSV with an unresolved within-week collision causes the
  generator to abort with a clear, per-collision error before any topic is
  written (no silent merge).

## Assumptions

- **The analyst edits `target_chapter`, not `chapter`.** The Pub10 week
  assignment is entered into the editable `target_chapter` column; the immutable
  `chapter` keeps the source deck title for provenance and as the renumber
  tie-break key, honouring the CSV identity contract.
- **Renumbering replaces letter suffixes entirely.** The previous
  `gram-05a`/`gram-05b` auto-disambiguation in the generator is removed;
  collisions are resolved by renumbering in the dedupe step, and any residual
  collision is a fail-fast error (FR-010).
- **Precedence is strict alphabetical on the source chapter** (then row order).
  The operator controls which deck keeps its numbers by naming the source
  folders so they sort in the desired order.
- **`target_gram_id` is added by the dedupe step, not the extractor** — exactly
  how `master_png_path` was introduced in feature 006. The analyst reviews/sets
  `target_chapter` *before* running the dedupe step; renumbering then runs over
  the signed-off weeks.
- **The week token is matched case-insensitively** as `Week` followed by an
  integer (`Week 1`, `Week 01`, `Week1`), capturing the integer with any leading
  zeros stripped.

## Out of Scope

- Choosing which week a Pub10 gram belongs to — that is an analyst decision
  entered into `target_chapter`; this feature only routes and renumbers.
- Changing the layout of non-`main` publications (progress tests, final
  assessment) — their per-publication folder shape is unchanged.
- Renumbering across weeks or globally — numbering is unique *within* a week
  only; the same number may recur in different weeks.
- Mutating `gram_id` or `topic_filename` — the renumbered value lives only in
  the additive `target_gram_id` column.

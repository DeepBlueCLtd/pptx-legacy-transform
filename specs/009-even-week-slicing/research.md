# Phase 0 Research: Even-slice no-week `main` decks

All decisions below are derived from the spec and the existing pipeline code
(`extract_to_csv.py`, `generate_dita.py`, `deduplicate_csv.py`). No external
research was required; the work is internal to the toolchain.

## R1 — Even-slice algorithm (contiguous blocks)

**Decision**: For a no-week `main` deck with G grams, week `w` (1-based) receives
a contiguous block of `floor(G/4)` grams, with the first `G mod 4` weeks taking
one extra. Grams keep source order; the first block → week 1, next → week 2, etc.
Per-gram week = the block its source index falls in.

**Rationale**: The stakeholders asked to "divide by 4 and put that many into each
week" — i.e. contiguous blocks, which also preserve the source grouping/adjacency
of grams within a deck. Remainder-to-earliest is the conventional deterministic
split (10 → 3/3/2/2).

**Alternatives considered**: Round-robin (`week = index % 4 + 1`) — rejected: it
interleaves grams rather than keeping the "that many per week" blocks, and
scatters originally-adjacent grams across weeks.

## R2 — Where slicing runs (extract, per-deck pass)

**Decision**: Compute the slice in `extract_to_csv.py` and write the assigned
week into `target_chapter`, as a per-deck pass once the deck's grams are
collected (it needs the deck total G and each gram's index). This replaces the
"leave `target_chapter` blank for an analyst" path **only** for no-week `main`
decks; a `Week N`-token deck still gets its single week (feature 008).

**Rationale**: `extract_to_csv.py` already owns `target_chapter` pre-population
(feature 008), so this is the smallest change to an existing stage (Principle II).
The slice is destination assignment, which belongs with the other destination
logic, not with the renumber.

**Alternatives considered**: A new dedicated slicing stage — rejected (YAGNI;
extract already does week assignment). Doing it in `deduplicate_csv.py` — rejected:
dedupe's job is number resolution, not week assignment; mixing them muddies both.

## R3 — Two numbering schemes and their renumber buckets

**Decision**: `deduplicate_csv.py:renumber_grams` gains a `main`-specific
numbering mode (non-`main` publications keep today's per-`(publication,
chapter, doc)` bump-on-collision behaviour unchanged):

- **continuous** (provisional default): treat the whole `main` publication as one
  numbering space. Order all `main` grams by `(week, source-chapter, row-order)`
  and assign `1..N` sequentially, so each week's grams are contiguous and week N
  begins at one past week N-1's maximum.
- **per-week**: bucket by `(main, week)`; within each week order by
  `(source-chapter, row-order)` and assign `1..k`.

Both write the assigned number into `target_gram_id`; `gram_id` is never mutated.
`(source-chapter, row-order)` is the ordering the existing renumber already uses,
so the two schemes differ only in bucket scope and whether numbering is contiguous
across week boundaries.

**Rationale**: Continuous delivers the author's stated "single numbering system —
week 2 may start at 35 after 10 grams land in week 1". Per-week is the likely
alternative. Confining both to one function with a mode parameter makes the
default a one-line choice.

**Consequence to surface (Principle VI)**: continuous numbering **re-sequences
existing `main` grams** — a gram an instructor knew as "Gram 25" in week 2 can
become "Gram 35". Per-week restart also renumbers but keeps each week starting at
1. This visible-number impact is exactly why the author's choice matters, and is
the reason `gram_id` (the original number) is preserved for traceability.

**Alternatives considered**: Bump-only for `main` (keep native numbers, bump only
collisions) — rejected: cannot produce the contiguous single-sequence the author
asked for. It is retained for non-`main` publications, which have no week IA.

## R4 — Flat `main` layout ⇒ drop `effective_doc` from the uniqueness scope

**Decision**: For `main`, remove the `doc-slug` path tier so grams land at
`main/week-N/gram-NN/`. Three call sites change in `generate_dita.py`:

1. `_publication_root` — do not append `doc_slug` for `main`.
2. `emit_main_ditamap` — drop the `doc_slug` segment from the topicref href (it
   already filters empty segments after feature 008's fix).
3. `check_row_identity` — for `main`, key the collision check on
   `(publication, effective_chapter, effective_number)` (drop `effective_doc`),
   matching the new folder scope.

The renumber bucket (R3) and this collision key must agree: both drop
`effective_doc` for `main`.

**Rationale**: With the doc tier gone, the folder is uniquely identified by
`(publication, week, number)`. If the collision key kept `effective_doc`, two
docs' grams could each keep number 5 in the same week and silently collide at
`main/week-1/gram-05/`. This is the central coupling called out in the spec.

**Alternatives considered**: Keep the doc tier — rejected; the deliverable
explicitly removes it. Non-`main` publications keep their existing path/scope.

## R5 — Toggle home and shape

**Decision**: A single `--main-numbering {continuous,per-week}` flag on
`deduplicate_csv.py`, defaulting to `continuous`. No other stage reads it.

**Rationale**: The renumber is the only stage that assigns numbers, so the scheme
belongs there; everything else stays scheme-agnostic. A CLI flag matches the
established pattern (`--final-pattern`, `--stub-wav`) and is air-gap-friendly (no
new dependency). Flipping the default later is a one-line `default=` change.

**Alternatives considered**: An environment variable or a CSV column — rejected:
less discoverable and inconsistent with the existing flag-driven stages.

## R6 — Determinism & idempotency

**Decision**: The slice is a pure function of per-deck gram index; the renumber is
a pure function of `(week, source-chapter, row-order)`. No wall-clock, no
hash-seeded ordering. Re-running yields byte-identical `target_chapter`,
`target_gram_id`, and generated output. Idempotency coverage is extended to assert
this under **both** schemes.

**Rationale**: Principle V. Continuous re-sequencing touches many rows but stays
deterministic because the ordering key is stable.

## R7 — Residual-collision fail-fast preserved

**Decision**: After the bucket change (R4), `generate_dita.py` still fails fast if
two distinct `main` grams resolve to the same `(week, number)` (e.g. dedupe was
not run), with the existing operator message pointing at the dedupe step.

**Rationale**: Principle IV / existing feature-008 behaviour — a real collision is
surfaced, never silently overwritten.

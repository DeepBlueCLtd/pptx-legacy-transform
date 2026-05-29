# Phase 0 Research — Week-Based IA

Decisions resolving the open questions, with rationale and rejected
alternatives. All confirmed with the stakeholder in the kickoff dialogue.

## R1 — Where the week number comes from

**Decision**: Extraction parses a `Week N` token (case-insensitive, optional
space, leading zeros stripped) from the `main` deck's folder title and writes
the bare integer `N` into the editable `target_chapter` column. The immutable
`chapter` keeps the full source title (e.g. `Instructor Week 1 Grams`).

**Rationale**: The folder titles already encode the week (`Instructor Week 1
Grams`). Deriving the number at extraction means the analyst sees `1`…`4`
pre-filled for the week decks and only has to fill in the genuinely-manual
cases (Pub10). Keeping the full title in `chapter` preserves provenance and
gives the renumber step a stable tie-break key.

**Rejected**: Storing the full `Week N` string in `target_chapter` — the
stakeholder asked for the bare integer (`1`…`4`), expanded to `Week N` only at
display time, so the CSV column stays terse and the analyst types a single
digit for Pub10.

## R2 — Pub10 and Final Assessment

**Decision**: The Final Assessment deck is a standalone publication (it already
matches the `final-assessment` pattern and is routed out of `main`). Pub10 grams
stay in `main`; an analyst is given a table of which week each Pub10 gram
belongs to and enters that week number into `target_chapter` per gram.

**Rationale**: Stakeholder direction. Final Assessment behaves like the progress
tests; Pub10 is real `main` content that needs human-assigned week placement,
which is exactly what an editable `target_chapter` is for.

## R3 — Renumbering order (which gram keeps its number)

**Decision**: Within a target-chapter bucket, distinct grams are processed in
**source `chapter` alphabetical order, then CSV row order**. The first claimant
of a number keeps it; a later gram whose number is already taken is reassigned
to one greater than the bucket's current maximum.

**Rationale**: Deterministic and explainable. The operator controls precedence
by naming source folders so they sort in the desired order (the stakeholder
will rename folders to force the native week deck ahead of injected Pub10
content). "max + 1" matches the stakeholder's phrasing and keeps renumbered
grams appended after the week's existing range rather than backfilling gaps.

**Rejected**: Backfilling the lowest free number — harder to predict and not
what was asked. Vessel-name or gram-id tie-breaks — less controllable than
folder naming.

## R4 — Where the renumbered value lands

**Decision**: A new optional right-edge column `target_gram_id`. Empty means
"unchanged — use `gram_id`". `gram_id` and `topic_filename` are never mutated.

**Rationale**: `gram_id` is an identity column the CSV contract says must not be
edited; renumbering is a *target* decision, so it belongs in a `target_*` column
exactly like `target_chapter` / `target_doc`. Additive right-edge placement
keeps older CSVs forward-compatible (FR-011), mirroring `master_png_path`
(feature 006). The generator derives the on-disk filename from the effective
number anyway, so `topic_filename` need not change.

**Rejected**: Overwriting `gram_id` + `topic_filename` in place — violates the
identity-column contract and loses the original number (the provenance that lets
a reviewer trace a renumbered gram back to its source).

## R5 — Removing the letter-suffix disambiguation

**Decision**: Delete `_compute_gram_suffixes` / `_suffix_for_row` and every
`suffix=` parameter. Grams group one topic per `(publication, effective chapter,
effective doc, effective gram number)`. Any residual collision is a fail-fast
error (R6), not an auto-suffixed folder.

**Rationale**: With renumbering doing the disambiguation in the CSV (where the
analyst can see and sign off the numbers), the generator no longer needs a
silent fallback. Removing it makes folder names uniformly `gram-NN`, satisfies
the stakeholder's "neater DITA", and is a net reduction in generator
complexity. The two mechanisms together would be redundant and could mask a
missing renumber run.

## R6 — Fail-fast on residual collisions

**Decision**: `check_row_identity` keys on `(publication, effective chapter,
effective doc, effective gram number, topic_type, sequence)` and aborts before
emission with one error per colliding slot, naming the grams and instructing the
operator to run the renumbering step.

**Rationale**: This is the safety net the suffix removal requires. Without it,
two distinct un-renumbered grams sharing a week+number would silently merge into
one topic (the exact data-loss bug the original identity check guarded against).
Keying on the *effective* number means a correctly renumbered CSV passes and an
un-renumbered one is rejected with an actionable message.

## R7 — Bare-integer chapter expansion

**Decision**: In `_normalise_chapter`, a purely-numeric effective chapter `N`
expands to display `Week N` and slug `week-N`. Non-numeric chapters keep the
existing `Instructor `-prefix handling.

**Rationale**: The stakeholder specified the column holds `1`…`4` "expanded into
`Week 1`". `_normalise_chapter` is already the single place that maps a raw
chapter to (audience-prefix, display, slug) and is used for both the on-disk
path and the navtitle, so expanding there keeps the map and the tree in agreement
with one change. The rule is general (any positive integer → `Week N`) so it is
robust if a fifth week is ever added.

## R8 — `target_doc` for `main`

**Decision**: For `main`, extraction passes `target_doc=""` so a week's grams
share one folder (`main/week-N/gram-NN`) with no per-document sub-segment.
Non-main publications keep their current `target_doc` behaviour.

**Rationale**: The new IA is "four folders, one per week" — a per-document
segment would re-introduce the per-deck slicing the feature removes. The
generator already omits the doc segment when `target_doc` is empty, so this is
the minimal change.

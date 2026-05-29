# Implementation Plan: Week-Based Information Architecture for `main`

**Branch**: `claude/fervent-goldberg-9M4pc` (developed on the existing working branch; no separate feature branch) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-week-based-ia/spec.md`

## Summary

Re-shape the `main` publication from "one chapter per source deck" (~12) into
exactly four week chapters. Two small, cohesive moves:

1. **Extraction** derives the week number from a `Week N` deck-folder title and
   writes the bare integer into the existing editable `target_chapter` column
   (immutable `chapter` keeps the full source title). For `main`, the
   per-document `target_doc` segment is dropped so every gram for a week lands
   directly under that week's folder. Decks without a week token (Pub10) get an
   empty `target_chapter` for the analyst to fill in.

2. **Renumbering** is added to `deduplicate_csv.py` (the existing dedupe
   post-processor) as a second, independent pass alongside large-asset
   redirection. Within each `(publication, effective chapter, effective doc)`
   bucket, distinct grams are walked in `(source chapter, row-order)` order; a
   gram whose number is already taken is reassigned to one past the bucket's
   current maximum, recorded in a new optional right-edge `target_gram_id`
   column. `gram_id` is never mutated.

The generator consumes both: it expands a bare-integer effective chapter to
`Week N` / `week-N`, derives every per-gram name from the **effective gram
number** (`target_gram_id or gram_id`), groups one topic per
`(publication, effective chapter, effective doc, effective gram number)`, and
**fails fast** on any residual collision. The old letter-suffix
auto-disambiguation (`gram-05a`/`gram-05b`) is removed entirely — renumbering
plus fail-fast replaces it.

The feature is **inert by default**: a CSV with no `target_gram_id` column
numbers straight from `gram_id` exactly as before (FR-011), and a `target_chapter`
equal to the source title reproduces the old per-deck slug.

**Edited files**: `extract_to_csv.py` (week-number derivation, drop `main`
`target_doc`), `deduplicate_csv.py` (renumber pass + `target_gram_id` column),
`generate_dita.py` (effective-gram-id naming, week-number chapter expansion,
remove suffix machinery, effective-id grouping + identity check, main ditamap by
effective chapter). Test extensions in the paired modules. Contracts and
`README.md` / `CLAUDE.md` updated. `introspect_pptx.py`, `mock_pptx.py`,
`publish_html.py`, and `rehydrate_dita.py` are unchanged.

## Technical Context

**Language/Version**: Python 3.9+ (`from __future__ import annotations`), no new
dependencies — only `re`, `csv`, `pathlib`, `collections` (all stdlib, already
imported). Tests stay stdlib `unittest`.

**Storage**: Filesystem only. The signed-off CSV gains one optional right-edge
column `target_gram_id`, written by `deduplicate_csv.py` (the extractor does not
emit it), mirroring how `master_png_path` was introduced in feature 006.

**Testing**: `python -m unittest discover tests/`. New assertions in
`tests/test_extract_to_csv.py` (week-number → `target_chapter`, `main`
`target_doc` empty), `tests/test_deduplicate_csv.py` (renumber order, max+1,
idempotency, inert when no collision), `tests/test_generate_dita.py` (week-number
expansion, effective-id paths/titles, no suffix folders, fail-fast on residual
collision, ditamap-by-week).

**Project Type**: CLI/script tool — same flat repo root, `verb_noun.py` scripts.

**Performance**: Renumbering is one O(rows) in-memory pass; no disk I/O. The
generator drops a pass (the suffix map) and gains none.

**Constraints**: Determinism/idempotency parity with features 001/004/006 —
renumbering recomputes from `gram_id` each run (clearing `target_gram_id` first,
exactly like `master_png_path`), so re-runs are byte-identical (FR-012).
Inert-by-default byte-identity (FR-011) preserved by reading `target_gram_id` via
`row.get(..., "")` and never adding it to the strict required-column set.

## Constitution Check

The project constitution is the unmodified Spec Kit template — no ratified
gates. The implicit principles features 001–006 honour hold here:

- **Simplicity / YAGNI**: One optional CSV column and one extra pass in an
  existing script; the generator *loses* code (the suffix machinery) net.
- **Backwards compatibility / inert-by-default**: `target_gram_id` read with an
  empty default; legacy CSVs number from `gram_id` unchanged (FR-011).
- **Determinism**: Fixed renumber order (FR-006); recompute-from-source each run
  keeps re-runs byte-identical (FR-012).
- **Fail-fast over silent loss**: residual within-week collisions abort with a
  clear error rather than merging grams (FR-010), replacing the old silent
  letter-suffixing.
- **Observability**: the renumber pass logs each reassignment (old→new, week)
  and a summary count to `dedup.log`; the generator logs collisions as errors.

**Result**: PASS — adheres to the implicit principles; no new dependencies, no
DTD changes, net reduction in generator complexity.

## Project Structure

### Documentation (this feature)

```text
specs/008-week-based-ia/
├── plan.md                       # This file
├── spec.md                       # Feature specification
├── research.md                   # Decisions: week token, renumber order, suffix removal, fail-fast
├── data-model.md                 # target_chapter (week int), target_gram_id, effective-id rules
├── quickstart.md                 # End-to-end walkthrough verifying SC-001…SC-006
├── contracts/
│   ├── csv-target-gram-id.md     # The optional target_gram_id column + renumber rules
│   └── week-chapter-mapping.md   # Week-token extraction + bare-int → Week N / week-N expansion
├── checklists/
│   └── requirements.md           # Spec quality checklist
└── tasks.md                      # Phase 2 task list
```

### Source Code (repository root)

```text
extract_to_csv.py     # MODIFIED — for `main`, derive target_chapter from a "Week N" deck
                      #   title (bare int, leading zeros stripped) and pass target_doc="" so a
                      #   week's grams share one folder; blank target_chapter when no week token.
                      #   Non-main publications unchanged. (FR-001, FR-002, FR-003)

deduplicate_csv.py    # MODIFIED — add a renumber pass: per (publication, effective chapter,
                      #   effective doc) bucket, walk distinct grams in (source chapter, row-order)
                      #   order; a taken number is reassigned to max+1 and written to the optional
                      #   right-edge target_gram_id column (gram_id untouched). Clears the column
                      #   first so re-runs are idempotent. (FR-005, FR-006, FR-007, FR-012)

generate_dita.py      # MODIFIED — effective gram number (target_gram_id or gram_id) drives folder
                      #   name, topic filename, topic id, and "Gram NN" title; bare-int effective
                      #   chapter expands to Week N / week-N; group one topic per (publication,
                      #   effective chapter, effective doc, effective gram number); fail-fast row
                      #   identity on that tuple; main ditamap grouped by effective chapter.
                      #   REMOVED — _compute_gram_suffixes / _suffix_for_row and all suffix params.
                      #   (FR-004, FR-008, FR-009, FR-010, FR-011, FR-013)

tests/
├── test_extract_to_csv.py   # EXTENDED — week-number → target_chapter; main target_doc empty
├── test_deduplicate_csv.py  # EXTENDED — renumber order/max+1, idempotency, inert-no-collision
└── test_generate_dita.py    # EXTENDED — week expansion, effective-id paths/titles/ditamap,
                             #   fail-fast on residual collision; REPLACES the auto-suffix test
```

Contracts updated: this feature's `contracts/` plus
`specs/001-pptx-dita-migration/contracts/csv-schema.md` (document the optional
`target_gram_id` column and the week-int meaning of `target_chapter`).
`README.md` and `CLAUDE.md` updated for the new pipeline step ordering and column.

**Structure Decision**: Same flat repository root as features 001–006. No new
top-level scripts — the renumber pass lives in the existing `deduplicate_csv.py`
because it is the same "post-process the signed-off CSV" stage and shares the
file-contract-preserving read/write helpers.

## Complexity Tracking

> No constitution violations. The only judgement call is *where* renumbering
> lives: it is added to `deduplicate_csv.py` rather than a new script because it
> is the same post-review CSV-rewrite stage, reuses the same utf-8-sig/CRLF
> read/write, and shares the "clear-then-recompute for idempotency" discipline
> already proven by the large-asset pass. Net, the generator becomes simpler
> (the suffix map and its threading through six functions are deleted).

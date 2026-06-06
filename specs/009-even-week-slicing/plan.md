# Implementation Plan: Even-slice no-week `main` decks across the four weeks

**Branch**: `009-even-week-slicing` | **Date**: 2026-06-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/009-even-week-slicing/spec.md`

## Summary

Distribute each no-week `main` deck's grams evenly across the four week folders
(an authorised replacement for the abandoned stakeholder week-assignment table),
flatten the `main` output to `main/week-N/gram-NN/` (no source-document tier), and
resolve the resulting gram-number collisions in the existing `deduplicate_csv.py`
renumber step. The `main` numbering scheme is a **toggle** on that step —
*continuous-across-weeks* (provisional default) or *per-week-restart* — so the
feature is complete regardless of the author's pending default choice. The change
is confined to three existing stages and adds no new script or dependency.

## Technical Context

**Language/Version**: Python 3.9 (WinPython 3.9.4 floor; `from __future__ import annotations`)
**Primary Dependencies**: `python-pptx ~= 1.0` (runtime baseline; unchanged — no new dependency)
**Storage**: Files — intermediate UTF-8-sig CSV; generated DITA tree on disk
**Testing**: Standard-library `unittest` (`python -m unittest discover tests/`); developer-time Jest layer unaffected
**Target Platform**: Air-gapped Windows (WinPython 3.9) + POSIX dev host
**Project Type**: Single project — flat single-purpose scripts at repo root
**Performance Goals**: Full corpus ~1,000 grams; slice/renumber are O(grams), trivially within budget
**Constraints**: Deterministic/idempotent output; stdlib-only tests; no runtime network; per-stage DEBUG log
**Scale/Scope**: ~15 decks / ~1,000 grams; touches 3 scripts (`extract_to_csv.py`, `generate_dita.py`, `deduplicate_csv.py`)

No blocking unknowns. The only deferred item — which numbering scheme is the
**default** — is non-blocking (both schemes are built; default is a one-line
provisional value). See spec **Deferred decisions**.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Air-Gapped, Self-Sufficient Operation** — PASS. No new dependency; the
  scheme toggle is a stdlib `argparse` flag. Python 3.9-safe. Tests stay
  stdlib-only. No network. Existing per-stage DEBUG logs are extended, not
  replaced.
- **II. Single-Purpose Scripts, Minimal Surface** — PASS. Capability is added as
  the smallest change to the three existing stages (extract assigns weeks,
  dedupe renumbers, generator lays out) — no new script, directory, or
  abstraction. The renumber **reuses** the existing `renumber_grams` mechanism
  rather than inventing a parallel one; the flat layout **removes** a path tier
  (less surface, not more).
- **III. Test-First Discipline** — PASS (committed). Each behavioural change ships
  with `unittest` coverage that fails before and passes after; the canonical
  suite stays green; nothing is skipped.
- **IV. Human-in-the-Loop Authority** — PASS *with note*. The even slice
  auto-fills `target_chapter` for no-week `main` decks, which previously was the
  analyst's manual call. This is not a silent guess: it is the stakeholders'
  explicitly-agreed policy (even distribution), `target_chapter` remains an
  **author-editable** column (any gram can be hand-reassigned), and the slice is
  documented. Authority is preserved; the default is just deterministic.
- **V. Deterministic, Idempotent Output** — PASS. Both the slice (function of
  per-deck gram index in source order) and the renumber (function of
  `(week, source-chapter, row-order)`) are pure and order-stable; the
  idempotency tests are extended to cover the new flow under both schemes.
- **VI. Honest Limitations** — PASS. The pending numbering-default decision, the
  retirement of the analyst-table path, and the consequence that continuous
  numbering re-sequences existing `main` gram numbers are all documented in the
  spec and `research.md`.

**Development-phase posture**: flattening the `main` layout and changing gram
numbering are output-shape changes; permitted pre-production and documented as
spec edge cases. No backward-compatibility binding.

**Result: PASS — no violations. Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/009-even-week-slicing/
├── plan.md              # This file
├── spec.md              # Feature spec (already written)
├── research.md          # Phase 0 — decisions (slice algorithm, numbering schemes, bucket change)
├── data-model.md        # Phase 1 — CSV columns, week assignment, numbering, path layout
├── quickstart.md        # Phase 1 — how to run the new flow + flip the scheme
├── contracts/           # Phase 1 — changed contracts (CSV, dedupe CLI, main path layout)
│   ├── csv-columns.md
│   ├── dedupe-cli.md
│   └── main-layout.md
└── checklists/
    └── requirements.md  # Spec quality checklist (already written)
```

### Source Code (repository root)

```text
extract_to_csv.py        # MODIFY: even-slice no-week main decks -> target_chapter (per-deck pass)
generate_dita.py         # MODIFY: flatten main path (drop doc-slug tier); drop effective_doc
                         #         from main's collision key (_publication_root,
                         #         emit_main_ditamap href, check_row_identity)
deduplicate_csv.py       # MODIFY: main numbering toggle (continuous|per-week) in renumber_grams;
                         #         new --main-numbering flag (default continuous); non-main unchanged

tests/
├── test_extract_to_csv.py    # even-slice distribution, remainder, source order, week-token untouched
├── test_generate_dita.py     # flat main layout, ditamap href, main collision key drops doc
└── test_deduplicate_csv.py   # both schemes, toggle/default, non-main unaffected, determinism
```

**Structure Decision**: Single-project, flat-script layout (Principle II). The
feature is three coordinated edits to existing stages plus their tests — no new
modules. The scheme toggle lives only in `deduplicate_csv.py`; `extract_to_csv.py`
and `generate_dita.py` are scheme-agnostic.

## Phase 0 — Research

See [research.md](./research.md). Resolves: the even-slice algorithm and where it
runs; the two numbering schemes and their renumber buckets; the flat-layout ⇒
drop-`effective_doc` coupling; the toggle's home; and the determinism strategy.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — the data entities (week assignment via
  `target_chapter`, effective number via `target_gram_id`, the `main` numbering
  space) and their rules.
- [contracts/](./contracts/) — the three contracts this feature changes: the CSV
  column semantics, the `deduplicate_csv.py` CLI (new `--main-numbering` flag),
  and the `main` output-path layout.
- [quickstart.md](./quickstart.md) — running extract → dedupe → generate for a
  corpus with a no-week deck, and flipping the numbering scheme.
- Agent context: `CLAUDE.md`'s feature-plan reference is updated to this plan.

## Complexity Tracking

No constitution violations — section intentionally empty.

# Implementation Plan: Frequency Bands

**Branch**: `claude/focused-ptolemy-fdl0ah` (spec dir `010-frequency-bands`) | **Date**: 2026-06-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/010-frequency-bands/spec.md`

## Summary

Correct the frequency-band model end to end. A gram's band is defined by the
GLC pair `bandwidth` + `bandcentre` (band = `[bandcentre - bandwidth/2,
bandcentre + bandwidth/2]`), not by `bandwidth` alone. The GLC parser gains
`bandcentre`; the CSV swaps its `freq_end` column in place for `bandwidth` and
`bandcentre`; the generator derives the true `freq-start`/`freq-end` for the
GramFrame `gram-config` table; the dedup view-key keys on the new pair; and the
sample/mock input data (mock_pptx + fixtures) carries `bandcentre` so tests
exercise the corrected path.

## Technical Context

**Language/Version**: Python 3.9 (WinPython 3.9.4.0 floor); `from __future__ import annotations`
**Primary Dependencies**: `python-pptx ~=1.0` (runtime); stdlib `xml.etree`, `csv`, `pathlib`. No new dependency.
**Storage**: Files — GLC XML in, CSV intermediate, DITA XML out
**Testing**: stdlib `unittest` (`python -m unittest discover tests/`); Jest layer (dev-time, html/) unaffected in contract but re-run via CI
**Target Platform**: Air-gapped Windows (WinPython REPL); dev hosts POSIX
**Project Type**: Single-project CLI pipeline (`scripts/` canonical + root REPL wrappers)
**Performance Goals**: N/A (batch, ~1000 grams, sub-minute test suite)
**Constraints**: Determinism/idempotency; missing-asset-dangles; stdlib-only tests; no network at runtime
**Scale/Scope**: ~15 decks, ~1000 grams; this change touches 4 scripts + contracts + tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Air-Gapped, Self-Sufficient Operation** — PASS. No new dependency; pure
  stdlib XML/CSV. Python 3.9 syntax preserved. Dual-logging unchanged. Missing
  `bandwidth`/`bandcentre` degrade with a warning (no crash, no network).
- **II. Single-Purpose Scripts, Minimal Surface** — PASS. Smallest change to
  existing stages (`extract_to_csv.py`, `generate_dita.py`, `deduplicate_csv.py`,
  `mock_pptx.py`); no new scripts, dirs, or abstractions.
- **III. Test-First Discipline** — PASS. New/updated unittest cases assert GLC
  parse of `bandcentre`, the CSV column swap, freq derivation in the gram-config
  table, and the dedup view-key. Suite must be green before merge.
- **IV. Human-in-the-Loop Authority** — PASS. The two real source values
  (`bandwidth`, `bandcentre`) are surfaced to the author in the CSV rather than a
  derived figure; missing values warn-and-defer, never fabricate.
- **V. Deterministic, Idempotent Output** — PASS. Deterministic numeric
  formatting (integer results without `.0`; canonical form otherwise); no
  timestamps or nondeterministic iteration. This is an intentional, reviewed
  change to generated output (gram-config table), which the constitution permits.
- **VI. Honest Limitations** — PASS. The real `source/` corpus lacks
  `bandcentre`; this is documented (Out of Scope) and the deprecated
  `wav_treatment` column remains noted.

**Development-Phase Posture**: Pre-production — no backward-compatibility binding
on the CSV contract, so swapping `freq_end` for `bandwidth`/`bandcentre` in place
is permitted; the in-tree `source.csv`-style fixtures are migrated to keep the
suite green and superseded shapes deleted.

No violations → Complexity Tracking omitted.

## Project Structure

### Documentation (this feature)

```text
specs/010-frequency-bands/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 — decisions (formatting, defaults, dedup key)
├── data-model.md        # Phase 1 — entities & field changes
├── quickstart.md        # Phase 1 — how to verify
├── contracts/           # Phase 1 — contract deltas for this feature
│   ├── glc-schema.md
│   ├── csv-schema.md
│   └── gramframe.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
scripts/
├── extract_to_csv.py      # GLC parser (parse_glc) + CSV column swap + row build
├── generate_dita.py       # gram-config table freq derivation + dedup view-key
├── deduplicate_csv.py     # view-key when pairing copy→master (freq_end → band pair)
└── mock_pptx.py           # emit GLC with <bandcentre>

specs/001-pptx-dita-migration/contracts/   # canonical contracts updated to match
├── glc-schema.md
├── csv-schema.md
└── gramframe.md

tests/
├── test_glc_parser.py     # parse bandcentre; missing-value warnings
├── test_extract_to_csv.py # CSV header/columns; row values
├── test_generate_dita.py  # gram-config freq derivation; dedup view-key
├── test_deduplicate_csv.py# view distinction by (bandwidth, bandcentre)
└── fixtures/              # minimal.glc / minimal.csv etc. carry bandcentre
```

**Structure Decision**: Single-project pipeline. Changes are confined to four
existing canonical scripts, their tests/fixtures, and the contract docs. No new
modules. The thin REPL wrappers at the repo root need no change (no new CLI
flags).

## Phase 0 — Research

See [research.md](./research.md). Resolves: numeric formatting of derived
limits, GLC element location/default for `bandcentre`, dedup view-key shape, and
negative-`freq_start` handling.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — GLC band settings, CSV row column delta,
  gram-config table derivation.
- [contracts/](./contracts/) — deltas to glc-schema, csv-schema, gramframe;
  the canonical contracts under `specs/001-.../contracts/` are updated during
  implementation to match.
- [quickstart.md](./quickstart.md) — verification steps.
- Agent context (`CLAUDE.md`) plan pointer updated to this plan.
```

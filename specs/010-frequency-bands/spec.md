# Feature Specification: Frequency Bands

**Feature Branch**: `claude/focused-ptolemy-fdl0ah` (spec dir: `010-frequency-bands`)
**Created**: 2026-06-19
**Status**: Draft
**Input**: GitHub issue #87 — "Frequency bands"

## Overview

A gram's spectrogram view has a frequency axis. The pipeline currently
mis-models that axis: it treats the GLC's `bandwidth` setting as the upper
frequency limit and hardcodes the lower limit to zero. In reality the band is
defined by **two** GLC settings working together — `bandwidth` (the width of the
band) and `bandcentre` (the centre point of the band, with `bandwidth / 2` on
either side). Frequency only starts at zero in the special case where
`bandcentre == bandwidth / 2`.

This feature corrects the model end-to-end: the extractor captures both values,
the human-edited CSV carries both, and the generator computes the true
`freq_start` and `freq_end` for the rendered GramFrame frequency table.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct frequency band in the published gram (Priority: P1)

A trainee opens a published gram whose source GLC declares a band that does not
start at zero (e.g. a band centred high in the spectrum). The interactive
spectrogram's frequency axis shows the true lower and upper limits of the band,
not `0 .. bandwidth`.

**Why this priority**: This is the whole point of the issue — the published
material currently shows the wrong frequency axis for any band not centred at
`bandwidth / 2`, which is a correctness defect in the delivered product.

**Independent Test**: Run the generator over a CSV row carrying a
`bandwidth`/`bandcentre` pair where `bandcentre != bandwidth / 2`, and confirm
the emitted gram-config table shows `freq-start = bandcentre - bandwidth/2` and
`freq-end = bandcentre + bandwidth/2`.

**Acceptance Scenarios**:

1. **Given** a GLC with `bandwidth = 400` and `bandcentre = 200`, **When** the
   gram is generated, **Then** the gram-config table shows `freq-start = 0` and
   `freq-end = 400`.
2. **Given** a GLC with `bandwidth = 400` and `bandcentre = 600`, **When** the
   gram is generated, **Then** the gram-config table shows `freq-start = 400`
   and `freq-end = 800`.
3. **Given** a GLC with `bandwidth = 100` and `bandcentre = 250`, **When** the
   gram is generated, **Then** the gram-config table shows `freq-start = 200`
   and `freq-end = 300`.

---

### User Story 2 - Technical author reviews frequency settings in the CSV (Priority: P2)

A technical author opens the extracted CSV in Excel to triage grams. Where the
CSV previously had a single `freq_end` column (the misleading upper limit), it
now shows `bandwidth` and `bandcentre` — the two values that actually define the
band — so the author reviews and, if needed, corrects the real source settings.

**Why this priority**: The CSV is the human-in-the-loop contract. The author
must see and reason about the same two values the source actually carries, not a
derived quantity.

**Independent Test**: Run extraction over a deck/fixture and confirm the CSV
header contains `bandwidth` and `bandcentre` in place of `freq_end`, populated
from the GLC.

**Acceptance Scenarios**:

1. **Given** a GLC carrying `bandwidth` and `bandcentre`, **When** extraction
   runs, **Then** the CSV row carries both values verbatim and no `freq_end`
   column exists.
2. **Given** a legacy/round-tripped CSV being consumed by the generator,
   **When** the generator reads it, **Then** it derives the band from
   `bandwidth`/`bandcentre`.

---

### User Story 3 - Deduplication still pairs grams that share a true view (Priority: P3)

The deduplication step pairs a copy gram to a master only when they present the
**same** time/frequency window. With the corrected model, "same frequency view"
means the same `(bandwidth, bandcentre)` pair, not the same single `freq_end`.

**Why this priority**: Deduplication correctness must not regress. Two grams
with identical `bandwidth` but different `bandcentre` are genuinely different
views and must not be deduplicated together; the old `freq_end`-only key could
mis-pair them.

**Independent Test**: Run dedup/generation over two grams with equal `bandwidth`
but differing `bandcentre` and confirm they are treated as distinct views (not
redirected to one another).

**Acceptance Scenarios**:

1. **Given** two audio grams with the same `bandwidth` and same `bandcentre`,
   **When** dedup runs, **Then** they are eligible to share one asset (same
   view).
2. **Given** two audio grams with the same `bandwidth` but different
   `bandcentre`, **When** dedup runs, **Then** they are treated as distinct
   views and not paired.

---

### Edge Cases

- **`bandcentre` missing from the GLC**: The audited source corpus today carries
  only `bandwidth`. Per the issue, the sample/mock input data is updated to carry
  `bandcentre`. For robustness, when `bandcentre` is absent the extractor records
  a warning (consistent with existing "GLC missing …" warnings) and leaves
  `bandcentre` blank; downstream the missing-asset/dangling-value conventions
  apply (the band is emitted with whatever is present, never crashing).
- **`bandwidth` missing**: As today, a warning is recorded and the value is left
  blank; the gram-config table degrades rather than crashing.
- **Odd `bandwidth`** (e.g. 401): `bandwidth / 2` is not an integer. The computed
  limits must be formatted deterministically and without spurious trailing
  `.0` for whole numbers.
- **Negative computed `freq_start`** (`bandcentre < bandwidth / 2`): emit the
  computed (possibly negative) value rather than silently clamping; the author
  sees the real source data. (Clamping behaviour is called out for clarification.)
- **Non-numeric `bandwidth`/`bandcentre`** in a hand-edited CSV: degrade with a
  warning rather than crashing the generator.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The GLC parser MUST read `settings/lofar/bandwidth` and
  `settings/lofar/bandcentre` from a GLC file, tolerantly (missing element →
  empty value plus a verbatim warning; never raises).
- **FR-002**: CSV extraction MUST replace the existing `freq_end` column,
  **in place at its current position**, with two columns named `bandwidth` and
  `bandcentre`, populated from the parsed GLC.
- **FR-003**: The identity-column / human-edited-contract conventions MUST be
  preserved: `bandwidth` and `bandcentre` are author-editable (not identity
  columns), written with the existing CSV encoding (UTF-8-with-BOM, CRLF,
  QUOTE_MINIMAL).
- **FR-004**: DITA generation MUST compute `freq_start = bandcentre - bandwidth/2`
  and `freq_end = bandcentre + bandwidth/2` and emit both into the GramFrame
  `gram-config` table, replacing the previous hardcoded `freq-start = 0` and
  `freq-end = bandwidth`.
- **FR-005**: Computed frequency limits MUST be formatted deterministically:
  integer-valued results render without a decimal point; non-integer results
  render in a stable, canonical form.
- **FR-006**: The deduplication view-key (the notion of "same frequency view"
  used to pair a copy gram with a master) MUST key on the corrected band
  representation (`bandwidth` + `bandcentre`) rather than the single `freq_end`.
- **FR-007**: Sample/mock input data MUST be updated so it exercises the new
  path: `mock_pptx.py` emits GLC files carrying both `bandwidth` and
  `bandcentre`, and test fixtures carry both values (including at least one band
  not centred at `bandwidth / 2`).
- **FR-008**: Behaviour MUST remain deterministic / idempotent: re-running the
  same CSV produces byte-identical DITA output, and re-extracting the same
  source produces byte-identical CSV.
- **FR-009**: Missing or unparseable `bandwidth`/`bandcentre` MUST degrade
  gracefully (warning + blank/best-effort output), never crash a run.
- **FR-010**: All affected contracts MUST be updated to match: the GLC schema
  (new `bandcentre`), the CSV schema (column swap), the gram-config/GramFrame
  contract (freq derivation), and the data model.

### Key Entities *(include if feature involves data)*

- **GLC band settings**: `bandwidth` (width of the frequency band) and
  `bandcentre` (centre frequency). Together they define the band:
  `[bandcentre - bandwidth/2, bandcentre + bandwidth/2]`.
- **CSV row (gram view)**: now carries `bandwidth` and `bandcentre` (replacing
  `freq_end`) plus the existing `time_end` and the other established columns.
- **GramFrame gram-config table**: the rendered frequency/time table whose
  `freq-start` and `freq-end` rows are derived from the band settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any gram whose source band is not centred at `bandwidth / 2`,
  the published frequency axis shows the true band limits (lower limit ≠ 0 when
  appropriate) — verifiable by inspecting the generated gram-config table.
- **SC-002**: 100% of extracted CSV rows expose `bandwidth` and `bandcentre`
  (no `freq_end` column remains), populated from the source GLC.
- **SC-003**: Two consecutive generation runs over an unchanged CSV produce
  byte-identical DITA output (determinism preserved).
- **SC-004**: The full stdlib `unittest` suite passes, including new cases that
  assert the freq derivation, the CSV column swap, the GLC parse of
  `bandcentre`, and the dedup view-key behaviour.
- **SC-005**: No new runtime dependency is introduced; tests remain
  stdlib-only and the Python 3.9 floor is respected.

## Assumptions

- The lower band limit is `bandcentre - bandwidth/2` and the upper is
  `bandcentre + bandwidth/2`; the special case `bandcentre == bandwidth/2`
  reproduces today's `freq_start = 0`, `freq_end = bandwidth` behaviour.
- `bandcentre` lives at `settings/lofar/bandcentre`, alongside the existing
  `settings/lofar/bandwidth` element in the GLC schema.
- "Swap in place" (per issue + maintainer decision) means `freq_end`'s position
  in the column order is taken by `bandwidth` then `bandcentre`; downstream code
  reads columns by name, so column order is for human (Excel) readability.
- Sample/mock input data is the place to introduce representative `bandcentre`
  values; the real `source/` corpus is not back-filled with invented values as
  part of this feature unless the maintainer supplies them.
- The `wav_treatment` column remains deprecated-but-retained, unchanged by this
  feature.

## Out of Scope

- Back-filling real, correct `bandcentre` values into the existing `source/`
  corpus (those values are not known to the pipeline; only sample/mock data is
  updated here).
- Any change to how the spectrogram image itself is rendered or cropped (only
  the frequency *table* metadata changes).
- The `time_start`/`time_end` axis (unchanged).

# Phase 0 Research: Frequency Bands

## R1 — Numeric formatting of derived frequency limits

**Decision**: Compute limits as exact values and format deterministically:
integer-valued results render with no decimal point (`400`, `0`); non-integer
results (from an odd `bandwidth`) render via a canonical, trailing-zero-stripped
decimal (e.g. `200.5`). Implement with a small helper that does integer
arithmetic where possible and strips a trailing `.0`.

**Rationale**: The existing gram-config table emits bare integer strings
(`"0"`, the raw `bandwidth`). Spurious `.0` would churn output and break the
determinism diff for the common (even-bandwidth) case. Stripping trailing zeros
keeps output stable and human-readable. No locale or float-repr nondeterminism
(values are small, exact halves at worst).

**Alternatives considered**: (a) Always float — rejected, introduces `.0` churn.
(b) Round to int — rejected, loses real half-Hz limits for odd bandwidths.

## R2 — `bandcentre` location and parse behaviour

**Decision**: Read `bandcentre` from `settings/lofar/bandcentre`, mirroring the
existing `settings/lofar/bandwidth` lookup in `parse_glc`. Missing/blank →
empty string + warning `"GLC missing bandcentre"`, exactly parallel to the
existing `"GLC missing bandwidth"` and `"GLC missing bottom_crop"` warnings.
`parse_glc` never raises.

**Rationale**: Sibling element placement is the natural GLC schema location and
matches `bandwidth`. Parallel warning text keeps the warn-and-defer contract
(Principle IV) consistent and greppable in logs.

**Alternatives considered**: A new `settings/lofar/band/centre` nesting —
rejected, no evidence for it and adds schema surface.

## R3 — Default when `bandcentre` is absent

**Decision**: Per maintainer direction, the **sample/mock input data is updated
to carry `bandcentre`**, so the primary path always has it. For real source GLCs
that lack it (today's corpus), the extractor warns and leaves `bandcentre`
blank. The generator then degrades: if `bandcentre` is blank it falls back to
the legacy interpretation (`freq_start = 0`, `freq_end = bandwidth`) so existing
real decks still render a sane table rather than crashing or emitting empties.

**Rationale**: This honours warn-and-defer (Principle IV) and missing-asset-
dangles (no crash) while making the corrected model the default for data that
carries both values. The legacy fallback equals `bandcentre == bandwidth/2`, the
documented special case, so it is a principled — not arbitrary — default.

**Alternatives considered**: Hard-fail on missing `bandcentre` — rejected,
would break every real deck today and violates warn-and-defer.

## R4 — Dedup view-key shape

**Decision**: Replace the `freq_end` element of the `.wav` view-key (in
`generate_dita.py`'s `_master_index_key`) with the band pair, sourced from the
CSV row's new `bandwidth` and `bandcentre` cells:
`("wav", png_path, time_end, bandwidth, bandcentre)`. `deduplicate_csv.py`'s
matching logic that compares the "same view" is updated to compare the same
pair. Image rows stay path-only (unchanged).

**Rationale**: "Same frequency view" must mean the same actual band. Two grams
with equal `bandwidth` but different `bandcentre` are different views and must
not be paired (Story 3). Keying on the raw pair (not the derived limits) avoids
any formatting-equivalence ambiguity and is the most direct representation.

**Alternatives considered**: Key on derived `(freq_start, freq_end)` — equivalent
in result but adds a derivation dependency into the key; rejected for directness.

## R5 — Negative `freq_start` (`bandcentre < bandwidth/2`)

**Decision**: Emit the computed value as-is (may be negative); do **not** clamp
to zero. The author sees the real source data and can correct it in the CSV.

**Rationale**: Clamping would hide a data error behind an optimistic default,
contrary to Honest Limitations (VI) and warn-and-defer (IV). A negative limit is
a visible signal of suspect source settings.

**Alternatives considered**: Clamp to 0 with a warning — viable, but hides the
discrepancy; revisit only if the maintainer asks.

## R6 — CSV column position ("swap in place")

**Decision**: In `CSV_COLUMNS`, the single `freq_end` entry is replaced by
`bandwidth, bandcentre` at the same position (between `time_end` and
`png_path`). All readers access columns by name (`row.get(...)`), so the change
is purely for the human reviewer's column ordering in Excel.

**Rationale**: Maintainer chose swap-in-place; pre-production posture permits the
CSV-contract change with fixture migration. Keeping the band columns adjacent to
`time_end` groups the view-defining metadata together for the author.

**Alternatives considered**: Append at right edge (forward-compat convention) —
explicitly overridden by maintainer for this feature.

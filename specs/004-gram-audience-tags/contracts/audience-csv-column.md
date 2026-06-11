# Contract: CSV `audience` Column

**Feature**: Per-Gram Audience Tags via CSV `audience` Column
**Status**: Draft (extends `specs/001-pptx-dita-migration/contracts/csv-schema.md`)

This contract defines the new 17th column on the intermediate
CSV (`source.csv`) and the rules the extractor and generator both
honour when writing and reading it. The position-17 numbering
assumes the in-feature cleanup to `csv-schema.md` (drop the stale
`analysis_docx_path` row that has never appeared in extractor
output) has landed; pre-cleanup the column would naïvely be
documented at position 18 even though the on-disk count is 17.

## 1. Column definition

| # | Column | Type | Empty allowed? | Notes |
|---|---|---|---|---|
| 17 | `audience` | string | yes | space-separated DITA audience tokens, each token a single word with a leading hyphen (e.g. `-own`, `-other`, `-trainee`); empty means "show in every edition" |

The column is appended at the right edge of the CSV (after
`warnings`, position 16). The position is fixed — any further
columns added by future features MUST be appended after this one.

## 2. Canonical form

A non-empty `audience` cell is:

- Trimmed (no leading or trailing whitespace).
- Single-space-separated between tokens (no tabs, no double spaces).
- Token order matches the source order in the PPTX descriptor when
  emitted by the extractor; preserved verbatim when emitted by a
  human editor.

The generator normalises whitespace on read (`" ".join(value.split())`)
before applying the per-gram consistency check, so a CSV with
non-canonical whitespace round-trips through the generator without
error.

## 3. Per-gram consistency

All CSV rows that share a `(publication, chapter, gram_id)` key MUST
carry the same `audience` value.

- **Writer (extractor)**: The extractor parses the descriptor once
  per gram and writes the resulting value to every row produced from
  that gram. The writer cannot violate the rule by construction.
- **Reader (generator)**: The generator groups CSV rows by
  `(publication, chapter, gram_id)` and asserts that the set of
  distinct (whitespace-normalised) `audience` values across the
  group has exactly one element. On violation, the generator raises
  a named exception whose message includes:
  - The publication name.
  - The chapter (or empty string for chapter-less publications).
  - The gram_id.
  - The conflicting values, deduplicated.

## 4. Token vocabulary (advisory)

This feature introduces two new audience tokens on top of feature
003's `-trainee`:

| Token | Meaning |
|---|---|
| `-trainee` | exclude from every student edition (feature 003) |
| `-own` | exclude from the own-nation student edition |
| `-other` | exclude from the other-nation student edition |

Any other token is allowed by the schema (the generator emits it
verbatim) but is treated as an unrecognised token: the generator
logs a WARNING line naming the gram and the token, and the build
proceeds. DITA-OT silently ignores audience tokens that no DITAVAL
profile names, so an unrecognised token is a no-op in publication.

A token with no leading hyphen (e.g. `own`) is an *include* token
under DITA's audience semantics, which is not what this feature
emits. The generator flags such tokens as an authoring error and
fails the build.

## 5. Backward compatibility (16-column legacy CSVs)

A CSV without the `audience` column (16 columns total) is accepted
by the generator and treated as if every row had an empty 17th
cell. The extractor always writes 17 columns; the generator
preserves a 17th column on output if its input had one.

This means:

- A pre-feature-004 CSV (`source.csv` from an older checkout) can
  be fed to the post-feature-004 generator and produces a working
  build with every gram visible in every edition.
- A post-feature-004 CSV can be fed to a pre-feature-004 generator
  (in the unlikely event of a roll-back) — the older generator will
  see the 17th column as an unknown extra field and ignore it
  (Python's `csv.DictReader` accepts extra fields silently).

## 6. Extractor behaviour (PPTX → `audience`)

The extractor function `_split_descriptor` (or equivalent) consumes
the slide header text and returns `(gram_id, vessel_name, audience)`.

### 6.1 Right-side bracket stripping

After splitting on the first colon, the right-hand side text is
repeatedly stripped of trailing `[…]` groups (each group is a single
pair of square brackets with non-bracket content inside; whitespace
between groups is optional). The captured inside-text values are
joined with a single space (in source order) and become the
`audience` cell value.

### 6.2 Whitespace handling

After bracket stripping, the right-hand-side `head` is stripped of
trailing whitespace and becomes the `vessel_name` value. Whitespace
between brackets is silently swallowed and does not appear in the
output.

### 6.3 No tags

A descriptor with no trailing brackets produces an empty `audience`
cell. Existing CSVs continue to parse identically to before this
feature.

### 6.4 Examples

| Input descriptor | `gram_id` | `vessel_name` | `audience` |
|---|---|---|---|
| `Gram 7: FR Vessel, Category 1, Bespin` | `7` | `FR Vessel, Category 1, Bespin` | (empty) |
| `Gram 7: FR Vessel, Category 1, Bespin [-own]` | `7` | `FR Vessel, Category 1, Bespin` | `-own` |
| `Gram 7: FR Vessel [-own][-other]` | `7` | `FR Vessel` | `-own -other` |
| `Gram 7: FR Vessel [-own] [-other]` | `7` | `FR Vessel` | `-own -other` |
| `Gram 7: [-other]` | `7` | (empty) | `-other` |
| `Gram 7` | `7` | (empty) | (empty) |

## 7. Generator behaviour (`audience` → DITA topicref)

The generator emits the `audience` cell value verbatim (after
whitespace normalisation) as the `audience="…"` attribute on the
gram's topicref in the parent ditamap.

- Empty cell → no `audience` attribute on the topicref.
- Non-empty cell → `audience="<value>"` on the topicref.
- The attribute is NOT propagated to the gram's `<topic>` element
  or to any element inside the topic file.

See `audience-dita-topicref.md` for the full DITA-side contract.

## 8. Human-editable cell

The `audience` column is the *one* CSV cell the author is
encouraged to hand-edit between extractor runs to broaden audience
tagging across the corpus. Hand-edited values are preserved across
generator runs but are overwritten by the next extractor run (the
extractor regenerates the CSV from PPTX). This matches every other
CSV cell's lifecycle.

Authors who want a hand-edit to survive a re-extraction MUST update
the PPTX descriptor to carry the corresponding bracketed tag.

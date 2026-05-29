# Feature Specification: Publication & Chapter Name Remapping via Lookup Table

**Feature Branch**: `claude/modest-dijkstra-g2DrC` (developed on existing working branch; no separate feature branch)
**Created**: 2026-05-28
**Status**: Draft
**Input**: User description: "Transform the name of some publications and chapters. They currently use the source names. Create a lookup table (CSV) that maps incoming `publication` and `chapter` names to different target names, used in the export-to-DITA phase."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rename chapters in the published output (Priority: P1)

A migration operator has extracted a corpus of legacy decks. The extracted
`chapter` values carry the source names exactly as they appeared in the
PowerPoint decks (e.g. `Instructor Week 1 Grams`). The operator wants the
published DITA to use cleaner, house-style chapter names (e.g. `Week 1 —
Passive Sonar`) without hand-editing every affected row in the extracted
CSV. They author a small lookup table once, listing each source chapter name
and the target name it should become, and re-run the DITA export.

**Why this priority**: This is the core of the request and delivers value on
its own — chapters are the most numerous and most frequently renamed of the
two fields. Renaming chapters alone is a complete, demonstrable improvement.

**Independent Test**: Provide an extracted CSV plus a lookup table containing
one or more `chapter` mappings, run the DITA export, and confirm the renamed
chapters appear in the generated chapter navtitles and folder paths while
unmapped chapters are unchanged.

**Acceptance Scenarios**:

1. **Given** an extracted CSV with chapter `Instructor Week 1 Grams` and a
   lookup table mapping that name to `Week 1 — Passive Sonar`, **When** the
   DITA export runs, **Then** the generated output uses `Week 1 — Passive
   Sonar` as the chapter navtitle and derives the chapter folder/path slug
   from the target name.
2. **Given** a chapter value that has no entry in the lookup table, **When**
   the export runs, **Then** that chapter is published unchanged (pass-through).
3. **Given** no lookup table is supplied at all, **When** the export runs,
   **Then** behaviour is identical to today (feature is inert / fully
   backwards compatible).

---

### User Story 2 - Rename publications in the published output (Priority: P2)

The same operator wants to rename one or more publications (the top-level
grouping the extractor assigns, e.g. `main`, `progress-test-1`,
`final-assessment-1`) to preferred display names in the published output,
again via the shared lookup table rather than per-row edits.

**Why this priority**: Publications are fewer and renamed less often than
chapters, but the operator wants one consistent mechanism for both fields.
Builds directly on the same lookup machinery as Story 1.

**Independent Test**: Provide a lookup table containing a `publication`
mapping, run the export, and confirm the publication's ditamap title and
output folder reflect the target name while unmapped publications are
unchanged.

**Acceptance Scenarios**:

1. **Given** a lookup table mapping publication `progress-test-1` to
   `Progress Test 1 — Spring Intake`, **When** the export runs, **Then** the
   publication's map title and output folder derive from the target name.
2. **Given** the lookup table contains both `publication` and `chapter`
   entries, **When** the export runs, **Then** each field is remapped only
   against entries declared for that field (a `chapter` entry never matches a
   publication value and vice versa).

---

### User Story 3 - Reuse one lookup table across repeated exports (Priority: P3)

The operator maintains the lookup table as a durable artefact and reuses it
across multiple extraction/export cycles as the corpus is re-processed, so
naming decisions are captured once and applied consistently every run.

**Why this priority**: Convenience and consistency over time; valuable but
not required for the first usable version.

**Independent Test**: Run the export twice with the same lookup table against
two different extracted CSVs and confirm consistent target naming in both.

**Acceptance Scenarios**:

1. **Given** a saved lookup table, **When** it is supplied to two separate
   export runs over different CSVs, **Then** any source name present in both
   CSVs is renamed identically in both outputs.

---

### Edge Cases

- **Unmapped names**: any `publication`/`chapter` value with no matching
  lookup entry passes through unchanged.
- **No lookup table supplied**: export behaves exactly as it does today.
- **Empty or header-only lookup table**: treated as "no mappings"; export
  proceeds unchanged, with an informational note.
- **Blank target name** for an entry: invalid; the entry is ignored and a
  WARNING is logged (a rename to nothing is never intended).
- **Duplicate source keys** for the same field (same field + same source
  name listed twice): a WARNING is logged and a single deterministic winner
  is chosen (last entry wins) so output stays predictable.
- **Many-to-one merge**: two different source names mapped to the *same*
  target name is permitted and intentional — the corresponding rows then
  share a publication/chapter folder in the output. Existing gram
  collision/auto-suffix handling continues to apply to any grams that land
  in the same bucket as a result.
- **Whitespace / case**: source names are matched after trimming surrounding
  whitespace; matching is otherwise exact and case-sensitive (see
  Assumptions).
- **Interaction with per-row chapter override**: when the extracted CSV
  carries a per-row `target_chapter` value, the lookup is applied to the
  *effective* chapter (the per-row override if set, otherwise the source
  `chapter`). For older CSVs lacking that column, the lookup applies directly
  to `chapter`.
- **Interaction with existing name normalisation**: any existing
  display/slug normalisation the export already performs (e.g. stripping an
  `Instructor ` prefix) is applied to the *mapped* target name, not the
  original source name.
- **Source name not present in any deck**: a lookup entry whose source name
  never appears in the CSV is harmless; optionally surfaced as an
  informational note so stale entries are visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The export-to-DITA phase MUST accept an optional, user-supplied
  lookup table (a CSV file) that maps source names to target names.
- **FR-002**: The lookup table MUST distinguish which field each mapping
  applies to, supporting at least the values `publication` and `chapter`.
- **FR-003**: For each row processed during export, the system MUST replace a
  `publication` value with its mapped target name when a `publication` entry
  for that source name exists.
- **FR-004**: For each row processed during export, the system MUST replace
  the effective `chapter` value with its mapped target name when a `chapter`
  entry for that source name exists, where "effective chapter" is the per-row
  override if present and non-empty, otherwise the source `chapter`.
- **FR-005**: Any `publication` or `chapter` value with no matching lookup
  entry MUST be published unchanged.
- **FR-006**: When no lookup table is supplied, output MUST be byte-for-byte
  equivalent to the current behaviour (the feature is opt-in and inert by
  default).
- **FR-007**: The target name MUST drive both the human-visible output (the
  publication's ditamap title and the chapter navtitle) AND the derived
  output paths/folder slugs, so the published artefact looks as though the
  content had been authored with the target name throughout.
- **FR-008**: Field matching MUST be scoped: a `chapter` mapping MUST NOT
  affect publication values, and a `publication` mapping MUST NOT affect
  chapter values.
- **FR-009**: The system MUST apply mapping before any existing display/slug
  normalisation (e.g. prefix stripping, slugification) so normalisation
  operates on the target name.
- **FR-010**: A lookup entry with a blank/missing target name MUST be ignored
  and reported as a WARNING.
- **FR-011**: Duplicate source keys within the same field MUST be resolved
  deterministically (last entry wins) and reported as a WARNING.
- **FR-012**: A missing, empty, or header-only lookup table MUST NOT abort the
  export; the run proceeds as if no mappings were declared, with an
  informational note.
- **FR-013**: The lookup table location MUST be discoverable/configurable by
  the operator (e.g. via a command-line option), consistent with how the
  export phase already takes its inputs.
- **FR-014**: Many-to-one mappings (distinct source names → one target name)
  MUST be permitted; rows sharing a resulting target name share the
  corresponding output bucket, and existing gram-collision handling continues
  to apply.

### Key Entities *(include if feature involves data)*

- **Name Mapping Entry**: a single remapping rule. Attributes: the *field* it
  applies to (`publication` or `chapter`), the *source name* (the value as it
  appears in the extracted CSV / source decks), and the *target name* (the
  value to publish). Source name + field together form the lookup key.
- **Lookup Table**: the collection of Name Mapping Entries, supplied as a CSV
  file separate from the extracted content CSV. Reusable across export runs.
- **Extracted Row** (existing): the per-gram record carrying `publication`,
  `chapter`, and (in newer CSVs) `target_chapter`; the values this feature
  reads and remaps during export.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can rename any number of chapters and publications
  for an export by editing a single lookup table, with zero edits to the
  extracted content CSV.
- **SC-002**: 100% of source names listed in the lookup table appear under
  their target names in the published output (titles, navtitles, and paths);
  0% of unlisted names are altered.
- **SC-003**: Running an export with no lookup table produces output
  identical to the pre-feature behaviour (no regressions).
- **SC-004**: A new operator can author a working lookup table and see the
  renamed output on their next export run without reading code — using only
  the column names and a short usage note.
- **SC-005**: Invalid entries (blank targets, duplicate keys) are surfaced as
  warnings rather than silently dropped or causing a crash, so the operator
  can correct the table.

## Assumptions

- **Matching semantics**: source-name matching is exact and case-sensitive
  after trimming surrounding whitespace. (Legacy chapter/publication values
  are already whitespace-normalised upstream, so trimming is sufficient; a
  fuzzier match was judged too risky for unintended renames.)
- **Lookup applies after per-row override**: the chapter lookup is applied to
  the *effective* chapter (per-row `target_chapter` if set, else `chapter`),
  per the user's confirmed precedence choice. This degrades gracefully for
  older CSVs (such as the current `source.csv`) that do not yet carry the
  `target_chapter` column.
- **Rename scope is "display + paths"**: per the user's confirmed choice, the
  target name fully replaces the source name everywhere downstream, including
  folder/path slugs, not only visible titles.
- **Publication values are the extractor's classified ids** (`main`,
  `progress-test-N`, `final-assessment-N`), not raw deck filenames; lookup
  `publication` source names must match those ids.
- **CSV format for the lookup table**: a small CSV with a header row naming
  the three concepts (field / source name / target name). Exact column names
  to be settled in planning; the spec only requires the three pieces of
  information be present.
- **The feature lives entirely in the export-to-DITA phase**; the extractor
  and the extracted CSV schema are unchanged by this feature.
- **No localisation/multi-language** target names in scope; target names are
  plain display strings in the same language as the source.

## Out of Scope

- Editing or rewriting the extracted content CSV itself.
- Remapping fields other than `publication` and `chapter` (e.g. `vessel_name`,
  `gram_id`) — the design should not preclude future fields, but only these
  two are required now.
- Pattern/regex or fuzzy matching of source names.
- Changes to the extraction phase or the introspect tooling.

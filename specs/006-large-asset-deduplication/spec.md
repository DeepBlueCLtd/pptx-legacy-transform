# Feature Specification: Large Asset Deduplication with Reversible Provenance

**Feature Branch**: `claude/amazing-brown-9Q3aj` (developed on existing working branch; no separate feature branch)
**Created**: 2026-05-29
**Status**: Draft
**Input**: User description: "The generated DITA document set is over 10Gb zipped because many very large `.wav` files appear in up to 10 locations. Post-process the CSV to introduce a column that redirects duplicate large files (over 10Mb) to a single master copy, so the DITA and HTML exports link many usages back to one physical file. For the DITA export, flag each lofar that has been redirected to a master file, recording the original path so the operation can be understood — and later reversed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Shrink the published set by redirecting duplicate large assets (Priority: P1)

A migration operator has generated a DITA document set that is too large to
move between machines — over 10Gb zipped — because the same large `.wav`
assets (and their `.glc` partners) are copied into many per-gram folders, in
some cases up to ten times. The operator wants the export to keep only **one**
physical copy of each large duplicated asset and have every other usage link
back to that single master copy, so the set shrinks dramatically without any
visible change to how a gram renders or plays.

**Why this priority**: This is the core of the request and delivers the
headline value on its own — eliminating the redundant large binaries is what
brings the set under the size limit and makes it movable.

**Independent Test**: Provide an extracted CSV in which a large (>10Mb) asset
is referenced by several grams, mark the duplicates to redirect to the first
instance, run the DITA export, and confirm the master asset is written exactly
once while every redirected gram links to it and renders/plays identically.

**Acceptance Scenarios**:

1. **Given** a large `.wav`/`.glc` asset referenced by five grams and a
   post-processed CSV that nominates the first gram's copy as the master and
   redirects the other four, **When** the DITA export runs, **Then** the
   master asset is written once and the four redirected grams link to that
   single copy rather than receiving their own copies.
2. **Given** a redirected gram, **When** its DITA topic is generated, **Then**
   the lofar renders (image) or plays/links (GLC viewer) exactly as it would
   if the asset had been copied locally — the redirection is invisible to the
   trainee.
3. **Given** the same large asset is used many times across the HTML export,
   **When** the HTML is published, **Then** each usage references the single
   shared file rather than a per-usage duplicate.

---

### User Story 2 - Understand and reverse the redirection later (Priority: P2)

The document maintainers value being able to pick up a gram's asset **adjacent
to its `.glc` / DITA parent** so they can move the pair into another part
(week) of the course. Because deduplication removes that adjacency for
redirected grams, the maintainers need each redirected lofar to carry enough
information to (a) see at a glance that it was redirected and where its file
originally belonged, and (b) mechanically re-introduce the duplicate later —
copying the master back to the gram's own folder and restoring the local link
— without consulting the original source corpus.

**Why this priority**: Reversibility is what makes the deduplication safe to
apply: it is a space optimisation the maintainers can undo per-gram when they
need the self-contained, movable pair back. It depends on Story 1 having
recorded the redirection.

**Independent Test**: Take a deduplicated export, read a redirected lofar's
recorded provenance, and confirm it contains everything needed to copy the
master file back into that gram's folder and restore a local link — with no
reference to the original extraction inputs.

**Acceptance Scenarios**:

1. **Given** a redirected lofar in a generated DITA topic, **When** the topic
   is inspected, **Then** it carries a machine-readable record of the asset's
   original (pre-dedup) path, distinguishable from a normal, non-redirected
   lofar by the presence of that record alone.
2. **Given** the recorded provenance plus the link to the master, **When** a
   rehydration step is applied, **Then** the master asset is copied back into
   the gram's own folder, the lofar's link is rewritten to the local copy, and
   the provenance record is removed — yielding a topic indistinguishable from
   one that had never been deduplicated.
3. **Given** a `.glc`/`.wav` pair, **When** rehydration runs, **Then** both
   the `.glc` and its adjacent `.wav` are restored together into the gram
   folder, preserving the adjacency the maintainers rely on when relocating a
   gram.

---

### User Story 3 - Apply deduplication as an optional post-processing step (Priority: P3)

The operator wants deduplication to be a deliberate, opt-in transformation of
the extracted CSV, not an always-on behaviour. With an un-processed CSV the
export behaves exactly as it does today (every asset copied locally); only when
the CSV has been post-processed to nominate masters and redirects does the
export deduplicate.

**Why this priority**: Keeps the feature safe and backwards compatible, and
lets the operator choose when the size/adjacency trade-off is worthwhile.

**Independent Test**: Run the export against an un-processed CSV and confirm
byte-for-byte equivalence with today's output; run it again against the
post-processed CSV and confirm deduplication occurs.

**Acceptance Scenarios**:

1. **Given** an extracted CSV with no redirection information, **When** the
   DITA export runs, **Then** output is identical to the current behaviour
   (feature is inert by default).
2. **Given** the post-processing step is run over a CSV, **When** it
   completes, **Then** only assets above the size threshold that genuinely
   duplicate another row are redirected; smaller or unique assets are left
   untouched.

---

### Edge Cases

- **No redirection information present**: export behaves exactly as today;
  every asset is copied into its own gram folder.
- **Asset at or below the size threshold**: never redirected, even if
  duplicated — the small `.glc` files and modest images are not worth the loss
  of adjacency. Only assets strictly over the threshold (10Mb) are candidates.
- **Unique large asset**: a large asset used in only one place has no
  duplicate to redirect to and is copied normally.
- **Master asset missing on disk**: handled like any other missing asset
  today — the link is still emitted (so re-running after dropping the file in
  resolves it) and a WARNING is logged; the redirected usages point at the
  same dangling master, not at separate dangling copies.
- **`.glc`/`.wav` pair**: the pair is treated as a single deduplication unit.
  The redirected lofar links to the **master `.glc`**, and the large `.wav`
  lives adjacent to that master `.glc` (never adjacent to the redirected
  gram). Deduplicating the `.wav` while leaving a local `.glc` — which would
  break the on-PC GLC viewer's adjacent-`.wav` lookup — is explicitly not
  done.
- **Chosen master is itself empty/invalid**: if the nominated master path is
  blank, the row is treated as non-redirected (no dedup applied) and a WARNING
  is logged.
- **Idempotent re-export**: re-running the export over the same post-processed
  CSV produces byte- and stat-identical output (no topic-file churn), matching
  the existing idempotency contract (R9).
- **Rehydration of an already-local lofar**: a lofar with no provenance record
  is left untouched by rehydration (it was never deduplicated).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The extracted CSV MUST be able to carry, per row, a redirection
  target identifying the single master copy a duplicated asset should link to,
  in addition to the row's own original asset path.
- **FR-002**: A post-processing step MUST be able to populate that redirection
  target by detecting duplicate assets across rows and, for duplicates whose
  size exceeds the threshold, nominating the first occurrence as the master
  and pointing the remaining occurrences at it.
- **FR-003**: The size threshold for redirection candidacy MUST be **strictly
  greater than 10Mb**; assets at or below the threshold MUST never be
  redirected.
- **FR-004**: During the DITA export, a row carrying a redirection target MUST
  link its lofar to the master copy instead of receiving its own copy of the
  asset, so the master binary is written exactly once.
- **FR-005**: A redirected lofar MUST render and behave identically to a
  non-redirected one from the trainee's perspective (image embeds, GLC-viewer
  links, and audio playback are unchanged).
- **FR-006**: Each redirected lofar in the generated DITA MUST carry a
  machine-readable record of the asset's **original (pre-dedup) path**, stored
  in a way that is valid against the existing DITA DTD (no DTD specialisation),
  survives the publishing toolchain, and is suppressed from the rendered
  trainee-facing HTML by default.
- **FR-007**: The presence of that provenance record alone MUST be sufficient
  to distinguish a redirected lofar from a normal one — no separate flag is
  required.
- **FR-008**: The provenance record plus the master link MUST together contain
  everything needed to reverse the operation (re-introduce the duplicate)
  without consulting the original extraction inputs.
- **FR-009**: For `.glc`/`.wav` pairs, the export MUST treat the pair as a
  single deduplication unit: the redirected lofar links to the master `.glc`,
  and the large `.wav` remains adjacent to that master `.glc`.
- **FR-010**: When a CSV carries no redirection information, the DITA export
  output MUST be byte-for-byte equivalent to the current behaviour (the
  feature is opt-in and inert by default).
- **FR-011**: The HTML export MUST reference the single shared master file for
  every usage of a deduplicated asset, rather than a per-usage duplicate.
- **FR-012**: A reverse (rehydration) operation MUST be able to consume a
  redirected lofar and produce a self-contained gram: copy the master asset
  (and, for a pair, its adjacent `.wav`) back into the gram's own folder,
  rewrite the lofar's link to the local copy, and remove the provenance
  record.
- **FR-013**: Re-running the export over an unchanged post-processed CSV MUST
  remain idempotent (byte- and stat-identical output).
- **FR-014**: Invalid redirection input (blank master target) MUST be treated
  as non-redirected and reported as a WARNING rather than aborting the export.

### Key Entities *(include if feature involves data)*

- **Original asset path** (existing, `png_path`): the row's own asset as named
  by the GLC's inner `data_source/filename` — the file this gram would copy
  locally absent deduplication. Its meaning is unchanged by this feature.
- **Master asset path** (new, proposed `master_png_path`): the path of the
  single master copy a redirected row should link to (the first occurrence of
  a duplicated large asset). Empty for non-redirected rows. Named to match the
  existing `png_path` convention even though the redirected assets are
  overwhelmingly `.wav`/`.glc`, not images.
- **Provenance record** (new, in the generated DITA): a DITA `<data>` element
  emitted as a child of the redirected lofar's `<section>`, carrying the
  original asset path as a name/value pair (proposed
  `<data name="original-asset-path" value="…"/>`). It is the sole flag that a
  lofar was redirected and the anchor for reversing the operation.
- **Deduplication unit**: for image lofars, the single image file; for audio
  lofars, the `.glc`/`.wav` pair handled together, with the link targeting the
  master `.glc`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a corpus where a large asset is duplicated *N* times, the
  deduplicated export contains exactly **one** physical copy of that asset
  (down from *N*), and the total set size falls accordingly — bringing the
  example corpus under the size needed to move it between machines.
- **SC-002**: 100% of redirected lofars render and play identically to their
  pre-dedup form for the trainee; 0% show a visible difference attributable to
  the redirection.
- **SC-003**: Every redirected lofar carries a recorded original path, and a
  reviewer can identify all deduplicated grams by that record alone, with no
  separate index.
- **SC-004**: A rehydration step can restore any redirected gram to a
  self-contained, movable form (master copied back, link localised, provenance
  removed) using only information present in the generated DITA — verified by
  the restored topic matching a never-deduplicated one.
- **SC-005**: Running the export over a CSV with no redirection information
  produces output identical to the pre-feature behaviour (no regressions).
- **SC-006**: Re-running the deduplicated export over an unchanged CSV
  produces byte- and stat-identical output (idempotent).

## Assumptions

- **Provenance representation**: the original path is stored as a DITA
  `<data name="original-asset-path" value="…"/>` element, a child of the
  redirected lofar's `<section>`. This was chosen over a custom attribute
  (DTD-invalid, rejected by Oxygen), over overloading `@outputclass` (a
  space-tokenised class list that paths would corrupt), and over `conref`/
  `conkeyref` (XML-element reuse, which neither reduces the binary file count
  nor fits binary dedup). `<data>` is part of the standard DITA metadata
  domain, validates without specialisation, round-trips through DITA-OT, and
  is suppressed from default XHTML output.
- **No separate "deduplicated" flag**: per the user's confirmed choice, the
  presence of the `<data>` element is itself the flag. A `deduplicated`
  `@outputclass` token was considered and dropped — its only unique value was
  cheap detection in *rendered HTML*, but `<data>` is suppressed from HTML
  anyway, and the maintainers' workflows (relocating grams, rehydrating) act
  on the DITA source where `<data>` is fully present and greppable. If a
  visible HTML badge is ever wanted, it can be reintroduced without changing
  the stored data.
- **Reversibility is mechanical from the element**: the master link (the
  redirected `href`) records *where to copy from*; the `<data>` value records
  *where the file is meant to sit locally* (the row's original path), from
  whose basename the deterministic local slug is recomputed. Together they let
  rehydration run as a pure inverse transform — no lookup against the original
  extraction inputs. A single `<data>` element per redirected lofar therefore
  suffices for both directions; no separate `dedup-master` record is needed.
- **`.glc`/`.wav` pairing**: the on-PC GLC viewer resolves a `.wav` adjacent to
  its `.glc`. The pair is deduplicated and rehydrated as a unit, with the link
  always targeting the `.glc`, so the viewer's adjacency assumption holds in
  both the deduplicated and rehydrated states.
- **Threshold is fixed at "over 10Mb"** per the user's stated cut-off; whether
  this is configurable is a planning detail, but the default is 10Mb.
- **Deduplication is a CSV post-processing + export-time concern**; the
  extraction phase and the introspect tooling are unchanged.
- **The new CSV column is additive**: older CSVs lacking it behave exactly as
  today (FR-010), consistent with how prior columns (`target_chapter`,
  `target_doc`, audience tags) were introduced.

## Out of Scope

- Changing the extraction phase or the introspect tooling.
- Deduplicating assets at or below the 10Mb threshold (e.g. small `.glc`
  files, modest images) — the loss of adjacency is not worth it for small
  files.
- A visible, trainee-facing or HTML-rendered badge marking deduplicated grams
  (the provenance is metadata only; a badge can be added later if wanted).
- Content-hash–based duplicate detection beyond what the post-processing step
  needs to identify duplicates (exact detection strategy is a planning detail).
- Automatically *choosing* which grams to relocate between course parts — this
  feature only makes the redirection visible and reversible; relocation
  remains a maintainer action.

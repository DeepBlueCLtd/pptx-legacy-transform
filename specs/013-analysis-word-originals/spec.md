# Feature Specification: Analysis-Sheet Word Originals

**Feature Branch**: `claude/dreamy-ramanujan-dj434q`
**Created**: 2026-08-07
**Status**: Draft
**Input**: User description: "On the gram pages, we show a screenshot of the analysis sheet. This is a screenshot of a MS-Word document. We have a process that took lots of screenshots. In the future, the analysts may wish to modify the analysis sheets, where the ms-word original is present. If .doc or .docx files are present in the gram folders, we should copy them to the DITA target folders." Plus, on review: "We don't need to include the Edit Source button. The document author will already have to be familiar working with the source materials. It is sufficient to just have the original MS-Word document." And: "With hindsight, I do not see any value in creating a MS-Word document containing a still of the static image."

## Overview

Every gram page shows its analysis sheet as an inline image — a PNG rendered
from a Word document by the prep-time snapshot stage (feature 007). That image
is a **dead end**: it is what the reader sees, but it cannot be amended. When an
analyst later needs to correct a bearing, a frequency, or a vessel identification
on a sheet, the editable Word document is back in the source tree, findable only
by someone who knows the legacy folder layout.

This feature carries the **editable original forward** so it sits in the same
folder as the gram's topic — the analyst opens the gram folder and the source
document is simply there, beside the image it produced.

Two linked changes deliver that:

1. **Copy the Word original into the gram's DITA topic folder.** Where a gram's
   analysis sheet is a genuine Word document in the source tree, that document
   travels alongside the rendered image. Nothing in the topic references it —
   no link, no button, no visible change for any reader. It is a source asset
   parked where the person who needs it will find it.

2. **Stop fabricating Word documents that contain only a picture.** The snapshot
   stage's reverse-wrap step (feature 007, FR-018) synthesises a minimal `.docx`
   wrapping the rendered PNG for any analysis image that has no Word sibling.
   That step is removed, and the wrappers it has already written are swept out.

The second change is not housekeeping — it is what makes the first change
trustworthy. The wrapper is created **precisely where no editable original has
ever existed**, and its entire content is the same picture the page already
shows. Once change 1 ships, the presence of a Word file in a gram folder is the
signal an analyst reads as "there is a source document here I can amend". The
wrapper makes that signal always true and therefore worthless: the analyst opens
it expecting a document and finds an uneditable image in a document-shaped
shell. An honest absence tells them to re-author the sheet; a fake tells them
nothing and wastes their time.

The wrapper also carries a latent defect. Its existence check looks only for a
same-stem `.docx`, never a `.doc`. In the older decks — whose analysis sheets
are legacy binary `.doc` files — every sheet therefore gets a bogus
`analysis.docx` fabricated next to the genuine `analysis.doc`, and a copy step
that reaches for the `.docx` picks the fake over the real document.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The editable analysis sheet travels with the gram (Priority: P1)

An analyst is asked to correct the analysis sheet for a gram — a frequency was
mis-transcribed. Today they read the value off the gram page's image, then go
hunting through the legacy source tree for the Word document that produced it,
guessing at deck and folder names. After this change they open the gram's own
folder in the DITA tree and the Word document is sitting beside `analysis.png`
under a predictable name. They edit it, re-run the prep and pipeline stages, and
the corrected sheet appears on the page.

**Why this priority**: This is the feature. Everything else exists to make this
signal honest.

**Independent Test**: Run the pipeline over a source tree containing one gram
whose analysis sheet is a genuine Word document with a rendered image sibling.
Confirm the gram's topic folder contains both the image and the Word document,
that the Word document is byte-identical to the source, and that the topic XML
and published HTML are unchanged from a run without the feature.

**Acceptance Scenarios**:

1. **Given** a gram whose analysis sheet is a `.docx` with a rendered `.png`
   sibling, **When** the pipeline runs, **Then** the gram's topic folder
   contains both the image and the Word document, and the Word document is
   byte-identical to the source file.
2. **Given** a gram whose analysis sheet is a legacy binary `.doc`, **When** the
   pipeline runs, **Then** the `.doc` is carried through in its original format
   — it is not converted, renamed to `.docx`, or dropped.
3. **Given** any gram, **When** the pipeline runs, **Then** the topic XML is
   byte-identical to what the previous release produced — the Word document is
   referenced by nothing.
4. **Given** a corpus that publishes cleanly today, **When** it is published
   after this change, **Then** the rendered output for every edition is
   byte-identical to the previous release.
5. **Given** a gram with a rendered analysis image but no Word original,
   **When** the pipeline runs, **Then** the topic folder contains the image
   alone, and the run reports no error for the absent document.
6. **Given** the same source tree run through the pipeline twice, **When** the
   two outputs are compared, **Then** the copied Word documents are byte- and
   timestamp-identical.

---

### User Story 2 — The pipeline stops fabricating picture-only Word documents (Priority: P1)

An operator runs the prep-time snapshot stage over a source tree. Today it
renders each Word sheet to an image **and** synthesises a `.docx` around every
image that lacks one. After this change it does the first job only. No Word
document is ever created by the pipeline; every Word document in the tree is one
an author wrote.

**Why this priority**: P1 alongside US1, and it must reach the delivered corpus
**with or before** US1. If the copy step ships while the snapshot stage is still
fabricating wrappers, analysts are handed fakes with no way to tell them from
real documents — strictly worse than today, where the wrapper is inert because
nothing consumes it.

**Independent Test**: Run the snapshot stage over a source tree holding an
analysis image with no Word sibling. Confirm no Word document is written, and
that no flag, argument, or configuration value can re-enable the behaviour.

**Acceptance Scenarios**:

1. **Given** an analysis image with no Word sibling, **When** the snapshot stage
   runs, **Then** no Word document is created for it.
2. **Given** a Word analysis sheet with no rendered image, **When** the snapshot
   stage runs, **Then** the image is rendered exactly as before — the
   Word-to-image direction is untouched by this feature.
3. **Given** any invocation of the snapshot stage, **When** its full set of
   options is inspected, **Then** there is no option that re-enables wrapper
   synthesis.

---

### User Story 3 — Wrappers already written are swept out of the source tree (Priority: P2)

The snapshot stage has already run over the existing source trees, so wrappers
are sitting in gram folders now; removing the step does not retract them. An
operator runs a sweep, which reports every fabricated wrapper it can find
without changing anything. Satisfied that the list contains no genuine documents,
they re-run it in apply mode and the wrappers are deleted.

**Why this priority**: P2 — required before the delivered corpus is trustworthy,
but separable from the code changes and safe to run at any point after them.
Follows the verify-then-apply convention the `ingest` stage already established,
because this is the one step in the feature that deletes files.

**Independent Test**: Over a tree holding a mix of fabricated wrappers, genuine
Word documents, and images, run the sweep in report mode and confirm it names
every wrapper and no genuine document; run it in apply mode and confirm exactly
the wrappers are gone.

**Acceptance Scenarios**:

1. **Given** a source tree containing fabricated wrappers, **When** the sweep
   runs in its default mode, **Then** it reports each wrapper and its count and
   deletes nothing.
2. **Given** the same tree, **When** the sweep runs in apply mode, **Then**
   exactly the reported wrappers are deleted and every other file is untouched.
3. **Given** a gram folder holding a genuine `.doc` and a wrapper `.docx`
   fabricated beside it, **When** the sweep runs in apply mode, **Then** the
   wrapper is deleted and the `.doc` survives.
4. **Given** a genuine author-written Word document that happens to contain a
   single full-page image, **When** the sweep runs, **Then** it is not reported
   and not deleted.
5. **Given** a tree the sweep has already cleaned, **When** it runs again,
   **Then** it reports nothing and changes nothing.

---

### User Story 4 — The operator can see how many grams have no editable original (Priority: P3)

An operator finishes an extraction and wants to know the scale of the gap: how
many grams show an analysis sheet that nobody can amend. The extraction summary
reports the count alongside the figures already there.

**Why this priority**: P3 — pure visibility. It changes no output, but it turns
"some grams have no Word original" from an unknown into a number the operator
can act on, and it is how the real corpus's proportions become known at all.

**Independent Test**: Extract from a tree with a known mix of grams with and
without Word originals and confirm the reported count matches.

**Acceptance Scenarios**:

1. **Given** a source tree in which some grams have Word originals and some do
   not, **When** extraction completes, **Then** the summary reports the number
   of grams whose analysis sheet has no Word original.
2. **Given** a tree where every gram has a Word original, **When** extraction
   completes, **Then** the reported count is zero.

---

### Edge Cases

- **A gram whose analysis sheet was never a Word document.** The newer decks
  supply the analysis sheet directly as an image. No Word document is copied,
  and this is a normal outcome — not a warning, not a skipped row. It is counted
  in the US4 coverage figure.
- **A gram with both a genuine `.doc` and a fabricated `.docx`.** The legacy-deck
  case the wrapper's `.docx`-only existence check creates. The sweep removes the
  fabrication; the copy step carries the `.doc`.
- **The Word original is missing or unreadable when the copy runs.** Warn and
  continue (the Zone C dangling rule). Because nothing references the document,
  there is no dangling href to repair — dropping the file in and re-running
  resolves it with no change to the topic XML.
- **The analysis sheet was recovered from a Lofar folder.** Extraction already
  recovers a sheet whose hyperlink went stale by finding one in the gram's own
  Lofar folder. The Word original is looked for beside the sheet at its
  **recovered** location, not at the stale hyperlink target.
- **The analysis sheet is dropped entirely.** A gram with no vessel name and an
  unresolvable analysis link already loses its analysis row. No row means no
  Word document to copy, and no coverage count.
- **A multi-page Word original.** The rendered image is page 1 only, with a
  warning — a known limitation of feature 007. The copied Word document carries
  every page, so this feature quietly mitigates that limitation for any gram
  whose original survives.
- **Two grams sharing one source analysis document.** Each gram's folder gets
  its own copy. The large-asset deduplication redirect (feature 006) covers
  Lofar images only and is not extended here; the analysis sheet's own image is
  already copied per-gram on the same basis.
- **An author edits the new CSV column.** It is author-editable data, not an
  identity column: a value that does not resolve warns and defers rather than
  failing the run.
- **A CSV written before this feature.** Reads forward-compatibly — the absent
  trailing cell behaves as empty, meaning "no Word original recorded".

## Requirements *(mandatory)*

### Functional Requirements

**Carrying the original forward (US1)**

- **FR-001**: Where a gram's analysis sheet resolves to a genuine Word document
  (`.doc` or `.docx`) in the source tree, the pipeline MUST copy that document
  into the gram's topic folder.
- **FR-002**: The copied document MUST take a stable, predictable name that
  mirrors the existing per-gram asset convention (`analysis.png` → `analysis.doc`
  / `analysis.docx`), so the folder is self-describing and the name does not vary
  with the source filename.
- **FR-003**: The document MUST be carried in its original format. A legacy
  binary `.doc` is copied as a `.doc`; nothing is converted, re-wrapped, or
  normalised.
- **FR-004**: The topic XML MUST NOT reference the copied document in any way —
  no link, no cross-reference, no conditional block. The rendered output for
  every edition MUST be byte-identical to the release before this feature.
- **FR-005**: The path to the genuine Word original MUST survive the extraction
  stage's existing redirect from the Word document to its rendered image, and
  MUST be recorded in the intermediate CSV so the generator consumes it from the
  CSV rather than re-deriving it from the source tree.
- **FR-006**: The new CSV field MUST be appended at the right edge of the schema,
  so CSVs written before this feature read forward-compatibly.
- **FR-007**: The new CSV field MUST be treated as author-editable, empty-allowed
  data. An empty value is the legitimate representation of "no Word original" and
  MUST NOT fail the run.
- **FR-008**: A recorded Word original that is absent or unreadable at copy time
  MUST warn and continue, never abort the run.
- **FR-009**: Copying MUST preserve the pipeline's determinism: two consecutive
  runs over an unchanged source tree produce byte- and timestamp-identical
  copies.

**Removing the fabrication (US2)**

- **FR-010**: The pipeline MUST NOT create Word documents. The snapshot stage's
  reverse-wrap behaviour is removed outright — not disabled by default — so no
  option, argument, or configuration value can re-enable it.
- **FR-011**: Feature 007's FR-018 (the guarantee that every analysis sheet
  exists in both an image and a Word form) is **superseded**. The guarantee is
  narrowed to the image side only; the Word side is now "present if an author
  wrote one, absent otherwise".
- **FR-012**: The Word-document-to-image rendering direction MUST be unaffected.

**Sweeping the existing trees (US3)**

- **FR-013**: The feature MUST provide a sweep that finds Word documents in a
  source tree that were fabricated by the removed reverse-wrap step.
- **FR-014**: Detection MUST be based on the fabricated document's **content
  signature** — the structural markers the wrapper writes — never on filename,
  timestamp, or file size, so a genuine document is never mistaken for a
  fabrication.
- **FR-015**: Detection MUST consider a fabricated document sitting beside a
  genuine `.doc`, which the removed step's `.docx`-only existence check allowed
  it to create.
- **FR-016**: The sweep MUST default to reporting only, and MUST require an
  explicit opt-in to delete — following the verify-then-apply convention already
  established for the destructive prep stage.
- **FR-017**: The sweep MUST report the number of documents it found, and (when
  applying) the number it deleted.
- **FR-018**: The sweep MUST be idempotent: running it over an already-swept tree
  reports nothing and changes nothing.

**Reporting coverage (US4)**

- **FR-019**: The extraction summary MUST report the number of grams that have an
  analysis sheet but no Word original, alongside the counts it already reports.

### Key Entities

- **Analysis Sheet**: The per-gram document recording the analyst's measurements
  and identification. Exists in the source tree as a Word document, an image, or
  both.
- **Analysis Image**: The rendered picture of the analysis sheet's first page.
  What the reader sees on the gram page. Unchanged by this feature.
- **Analysis Word Original**: The editable Word document an author wrote. The
  asset this feature preserves. Not every analysis sheet has one, and the
  pipeline never creates one.
- **Wrapper Document**: A Word document fabricated by the removed reverse-wrap
  step, whose only content is an analysis image placed full-page. Carries no
  editable text. Identified by content signature and deleted by the sweep.
- **Gram Topic Folder**: The per-gram output folder holding the topic and every
  asset it needs under stable bare filenames. Gains the Word original as a
  parked, unreferenced source asset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of grams whose source carries an author-written analysis
  document have that document available in the gram's own output folder.
- **SC-002**: Zero output folders contain a Word document whose only content is
  a picture of the analysis sheet.
- **SC-003**: The published output for every edition is byte-identical before and
  after this feature — no reader sees any change.
- **SC-004**: An analyst locates the editable sheet for any given gram without
  searching the legacy source tree: it is in the same folder as the gram's page.
- **SC-005**: After a sweep, the number of surviving fabricated wrappers is zero
  and the number of genuine documents lost is zero.
- **SC-006**: A single line of the extraction summary tells the operator how many
  grams have no editable analysis original.
- **SC-007**: Two consecutive pipeline runs over an unchanged source tree produce
  identical output, including the newly copied documents.

## Assumptions

- **The Word original is the same-stem sibling of the rendered image**, per the
  convention the snapshot stage already establishes. A gram whose Word document
  sits elsewhere under a different stem is out of scope.
- **One analysis sheet per gram.** Grams with multiple Word sheets are not
  contemplated; the existing pipeline already carries a single analysis row.
- **The copied document reaches the DITA tree only, not the published HTML.**
  Nothing references it, and unreferenced files are not carried into rendered
  output. This is intended: analysts work in the DITA source, and copying it into
  every edition would multiply the transfer cost for no reader benefit.
- **Analysts have MS Word.** Legacy binary `.doc` files are carried as-is rather
  than converted, on the basis that the people who need to edit them have the
  application that reads them.
- **The corpus committed in this repository is a mock tree**, not the real AAAC
  decks. Its mix of analysis-sheet formats therefore says nothing about the real
  corpus's proportions — which is precisely what FR-019's coverage count exists
  to reveal on the target.
- **Wrappers are already present in existing source trees** from previous
  snapshot runs, so removing the step (US2) does not by itself clean the corpus;
  the sweep (US3) is required.
- **No backward-compatibility obligation** binds the CSV shape (pre-production
  posture). The new field is nonetheless appended at the right edge, matching the
  house rule that keeps older CSVs readable.
- **The sweep is a prep-time operation**, run by an operator against a source
  tree, not part of the forward data flow.

## Dependencies

- Builds on **feature 007 (analysis-sheet images)**, whose snapshot stage renders
  the Word sheets and whose FR-018 this feature supersedes.
- **US2 must reach the delivered corpus with or before US1.** Shipping the copy
  step while wrappers are still being fabricated would hand analysts documents
  they cannot distinguish from genuine originals.
- No new runtime dependency. The work is file copying and archive inspection,
  both of which the pipeline already does with the standard library.

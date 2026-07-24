# Feature Specification: Demon Images

**Feature Branch**: `claude/gh-issue-151-spec-m43omp`
**Created**: 2026-07-24
**Status**: Draft
**Input**: GitHub issue #151 "Demon images": "We've had a download of images, which are being used to replace some .wav files. We've already introduced the `ingest` script that copies images to their new location. In the new download of images, some extra images have been added. These are called 'demon' images, and have been produced by using an alternate mathematical rendering algorithm. Filenames for these demon images will be things like `Demon - 10m2s 0-40Hz.png` and `Demon - 0-40Hz.png`. We need to create new GramFrame components for the demon images. Their time period will be the image height in pixels, and the frequency range will always be 0 - 40 Hz. The demon gramframe will be the first one on the page for a gram (after the analysis sheet if it's an instructor). To prove this we'll introduce some stock images with filenames like the ones above, and modify the ingest process to create a `demon.glc` file in the target folder if there's a demon image available. The `demon.glc` will be a copy of the first hyper-linked glc for that folder. Later, in the `extract` process, when we are processing a gram from a pptx slide, we should check if there is a `demon.glc` in that folder, and create a CSV entry for the demon image — placing it before the other gramframe entries for that gram. Here is a stock image that we'll use for demon in test data. Copy it into the root folder, called `demon_stock.png`."

## Overview

A "demon" image is a second, alternately-rendered view of a gram, produced by
a different mathematical rendering algorithm than the standard spectrogram. It
arrives in the same author *incoming* delivery tree already handled by the
`ingest` stage (`ingest_gram_images.py`), but it is **not** a replacement for a
`.wav` — it is an *additional* GramFrame that leads the gram's page.

The demon image differs from an ordinary imported gram image in three ways:

1. Its **time period** (GramFrame y-axis) is the image's pixel height, exactly
   as issue #148 already establishes for every image gram — the demon carries
   no separate duration.
2. Its **frequency range is always 0 – 40 Hz**, regardless of the gram's other
   Lofar bands.
3. It **renders first** on the gram's page — before every Lofar GramFrame, and
   (for the instructor edition) immediately after the analysis-sheet section.

Unlike the existing image-import flow, a demon image is **not matched to a
`.wav` stem**. Its presence is signalled by a `demon.glc` marker file that
`ingest` creates in the gram folder; `extract` discovers that marker while
processing the gram's slide and emits a dedicated CSV row for it. The demon
image sits alongside — never replaces — the gram's existing Lofar assets.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ingest seeds a demon marker for each delivered demon image (Priority: P1)

The author's incoming delivery tree (already the input to the `ingest` stage)
now also contains demon screenshots, named with a leading `Demon` token, e.g.
`Demon - 10m2s 0-40Hz.png` or `Demon - 0-40Hz.png`, dropped into the same
incoming gram folders as the `.wav`-replacement screenshots. The operator runs
`ingest` in its default **verify** mode and sees each demon image reported in a
distinct `DEMON IMAGES` section (read-only, nothing written). Satisfied, the
operator re-runs with `--apply`. For every demon image in a matched gram folder
the tool copies the image into the **source** gram folder keeping its original
`Demon - …` filename, and writes a `demon.glc` marker beside it — a copy of the
gram folder's **first hyperlinked `.glc`** with two edits: its referenced
`<filename>` repointed to the copied demon image, and its band settings
overwritten to encode the fixed **0 – 40 Hz** range.

**Why this priority**: Nothing downstream can surface a demon GramFrame until
the marker exists in the source tree. This story creates the on-disk contract
(`demon.glc` + copied image) that `extract` (US2) consumes; it is the
foundation of the feature.

**Independent Test**: Run `--apply` over a synthetic incoming gram folder that
holds one `Demon - 0-40Hz.png`, against a source gram folder that holds a
hyperlinked Lofar `.glc`. Confirm the source folder gains `Demon - 0-40Hz.png`
(byte-identical to the incoming image) and a `demon.glc` whose `<filename>`
names that image and whose band settings encode 0 – 40 Hz; confirm the incoming
tree is unchanged.

**Acceptance Scenarios**:

1. **Given** an incoming gram folder containing exactly one demon image and a
   matched source gram folder with at least one hyperlinked `.glc`, **When**
   `--apply` runs, **Then** the source gram folder contains a copy of the demon
   image under its original name and a `demon.glc` marker referencing it.
2. **Given** that `demon.glc` is created, **When** its contents are inspected,
   **Then** it is a copy of the folder's first hyperlinked `.glc` with only its
   referenced `<filename>` and its band settings changed — every other element
   preserved.
3. **Given** the created `demon.glc`, **When** the frequency range is derived
   from its band settings the way the generator derives every gram's band,
   **Then** the derived range is 0 – 40 Hz.
4. **Given** a demon image is present, **When** `ingest` runs in default
   **verify** mode, **Then** the demon image is listed in a `DEMON IMAGES`
   report section and nothing on disk is created or modified.
5. **Given** a gram folder that already holds a `demon.glc` from an earlier
   run, **When** `--apply` runs again, **Then** the marker is not duplicated and
   the run reports the demon as already present — the operation is idempotent.
6. **Given** an incoming gram folder holding two or more demon images, **When**
   `--apply` runs, **Then** one marker is created per demon image (`demon.glc`,
   `demon-2.glc`, … in incoming-filename order), each repointed at its own
   image.

---

### User Story 2 — Extract emits a leading demon row per gram (Priority: P1)

When `extract` processes a gram from its pptx slide, after resolving the gram's
Lofar `.glc` files it checks the folder of the gram's **first resolved Lofar
`.glc`** for one or more `demon.glc` markers. For each marker found it emits a
CSV row for the demon image — a new `topic_type="demon"` row — carrying the
demon image path, the image's pixel height as the time period, and the fixed
0 – 40 Hz band read straight from `demon.glc`. The demon row(s) are ordered
**before** the gram's Lofar rows in the CSV so the demon GramFrame leads the
page.

**Why this priority**: This is the stage that turns the on-disk marker into
publishable content. Without it the marker seeded in US1 has no effect.

**Independent Test**: Point `extract` at a synthetic content tree whose gram
folder holds a Lofar `.glc`, a `demon.glc` referencing a demon PNG, and that
PNG. Confirm the emitted CSV contains a `topic_type="demon"` row for the gram
with `time_end` equal to the PNG's pixel height, a 0 – 40 Hz band, and an
ordering that places it ahead of the gram's Lofar rows.

**Acceptance Scenarios**:

1. **Given** a gram whose first Lofar `.glc` folder contains a `demon.glc`,
   **When** `extract` runs, **Then** the CSV gains one `topic_type="demon"` row
   for that gram, sharing the gram's `topic_filename`.
2. **Given** the demon image on disk, **When** the demon row is written, **Then**
   its `time_end` equals the demon image's pixel height (scan-line count), per
   the issue #148 image-height rule already used for Lofar image grams.
3. **Given** the `demon.glc` band settings, **When** the demon row is written,
   **Then** its band columns encode the 0 – 40 Hz range.
4. **Given** a gram with both a demon and one or more Lofars, **When** the rows
   are ordered, **Then** the demon row precedes every Lofar row for that gram.
5. **Given** a gram folder with several `demon.glc` markers, **When** `extract`
   runs, **Then** one demon row is emitted per marker, ordered deterministically
   (marker-filename order) ahead of the Lofars.
6. **Given** a gram whose first Lofar `.glc` folder holds no `demon.glc`,
   **When** `extract` runs, **Then** no demon row is emitted and the gram's rows
   are exactly as before this feature.

---

### User Story 3 — Generate renders the demon GramFrame first (Priority: P1)

The generator merges a gram's rows into one topic. It now emits the demon
GramFrame block(s) immediately after the analysis-sheet section and before the
Lofar blocks. The demon block is an ordinary inline image GramFrame table
carrying the demon image, its pixel-height time period, and the 0 – 40 Hz band.
The demon block is shown to **all** audiences (it is regular gram content, not
instructor-gated like the analysis sheet); in the student editions — where the
analysis section is filtered out — the demon block becomes the first block on
the page.

**Why this priority**: This story delivers the visible outcome the issue asks
for: a demon GramFrame leading each gram's page.

**Independent Test**: Generate a topic from a CSV containing one demon row and
two Lofar rows for a gram. Confirm the topic body's first content block (after
the instructor-only analysis section) is the demon GramFrame table, followed by
the two Lofar tables in `sequence` order, and that the demon block carries no
audience restriction.

**Acceptance Scenarios**:

1. **Given** a gram with a demon row and Lofar rows, **When** the topic is
   generated, **Then** the demon GramFrame table appears before every Lofar
   GramFrame table in the topic body.
2. **Given** an instructor edition, **When** the topic is generated, **Then**
   the block order is analysis sheet, then demon, then Lofars.
3. **Given** a student edition (analysis section filtered), **When** the topic
   is published, **Then** the demon GramFrame is the first block on the page.
4. **Given** the demon row's `time_end` and 0 – 40 Hz band, **When** the demon
   GramFrame is emitted, **Then** the table presents the pixel-height time
   period and a 0 – 40 Hz frequency range.
5. **Given** the demon image, **When** the topic folder is assembled, **Then**
   the demon image is copied beside the topic under a stable bare filename
   (`demon.png`, `demon-2.png`, …) so its `href` needs no `../` traversal.
6. **Given** a gram with multiple demon rows, **When** the topic is generated,
   **Then** each demon renders as its own leading GramFrame in row order, ahead
   of the Lofars.

---

### Edge Cases

- **Demon image missing on disk** (a `demon.glc` marker whose referenced image
  is absent) → the demon row dangles per the pipeline's missing-asset rule: the
  topic still emits the demon block with its intended local `href` and an
  `ASSET_MISSING` flag; dropping the image in and re-running resolves it. A
  blank `time_end` from an absent image is an asset problem, not a fail-fast
  (mirrors the Lofar image rule).
- **Demon image present but pixel height unreadable** (unrecognised/corrupt
  format) → the demon row keeps a blank `time_end` and records a "time period
  unknown" warning; it does not crash the run.
- **`demon.glc` is malformed / has no inner `<filename>`** → treated as an
  unreadable GLC per the pipeline's forgiving boundary-parsing: warn and skip
  that marker; other markers and the gram's Lofars still process.
- **Gram has a demon but no resolvable Lofar `.glc`** (so there is no "first
  Lofar folder" to inspect) → no demon row is emitted; the demon marker, if any,
  is not discovered. (Demon discovery is anchored to the gram's first resolved
  Lofar folder by design; a gram with no resolvable Lofar is already degenerate.)
- **Demon image in the incoming tree whose gram/document folder does not match
  the source tree** → reported by the existing unmatched-folder machinery; no
  marker is created until the operator fixes the incoming tree and re-runs.
- **A non-demon image that merely happens to contain the word "demon" mid-name**
  → only a leading `Demon` token (case-insensitive) is treated as a demon image;
  a stem like `WAV demon 1` is matched by the existing wav-replacement flow, not
  the demon flow.
- **Demon filename tokens** (`10m2s`, `0-40Hz`, and a leading duration prefix
  such as `4m10s_`) → decorative; the time period comes from pixel height and the
  band is the fixed 0 – 40 Hz. The tokens are neither parsed nor validated.
- **Idempotent apply** → a second `--apply` over an already-seeded gram does not
  create a duplicate marker or re-copy the image with a changed name; the run
  reports the demon as already present.

## Requirements *(mandatory)*

### Functional Requirements

#### Ingest (marker creation)

- **FR-001**: `ingest` MUST recognise an incoming image carrying a `Demon` token
  (case-insensitive) as a **demon image**, distinct from the existing
  `.wav`-replacement screenshots, and MUST NOT attempt to match it to a `.wav`
  stem. The token is either at the start (`Demon - 0-40Hz.png`,
  `Demon - 10m2s 0-40Hz.png`) or immediately after a leading duration token and
  a space/underscore separator (`4m10s_Demon - 0 - 40 Hz.jpg`); the duration
  prefix, like the other filename tokens, is decorative (FR-024).
- **FR-002**: `ingest` MUST accept demon images with `png`, `jpg`, and `jpeg`
  extensions (case-insensitive), consistent with the existing incoming-image
  set.
- **FR-003**: In default **verify** mode `ingest` MUST report each demon image
  in a distinct `DEMON IMAGES` report section and MUST NOT create, modify, or
  copy anything on disk.
- **FR-004**: In `--apply` mode, for each demon image in a matched source gram
  folder, `ingest` MUST copy the image into the source gram folder **keeping
  its original filename**.
- **FR-005**: In `--apply` mode `ingest` MUST create a `demon.glc` marker in the
  source gram folder as a **copy of that folder's first hyperlinked `.glc`**,
  with exactly two changes: (a) its referenced `<filename>` repointed to the
  copied demon image, and (b) its band settings overwritten so the derived
  frequency range is **0 – 40 Hz**; every other element MUST be preserved
  byte-for-byte.
- **FR-006**: When a gram folder holds more than one demon image, `ingest` MUST
  create one marker per image, named `demon.glc`, `demon-2.glc`, `demon-3.glc`,
  … in deterministic incoming-filename order, each repointed at its own image.
- **FR-007**: Demon marker creation MUST be idempotent: re-running `--apply`
  over a gram that already carries its demon marker(s) MUST NOT duplicate a
  marker or produce a differently-named copy, and MUST report the demon as
  already present.
- **FR-008**: `ingest` MUST leave the demon flow strictly additive — the
  existing `.wav`-replacement matching, apply behaviour, report sections, and
  the wav-left-in-place policy MUST be unchanged.

#### Extract (row emission)

- **FR-009**: When processing a gram, `extract` MUST inspect the folder of the
  gram's **first resolved Lofar `.glc`** for one or more `demon.glc` markers
  (case-insensitive `demon*.glc`).
- **FR-010**: For each demon marker found, `extract` MUST emit one CSV row with
  `topic_type="demon"`, sharing the gram's `topic_filename`, `publication`,
  `chapter`, routing, and identity fields.
- **FR-011**: Each demon row's `time_end` MUST be the demon image's pixel height
  (scan-line count) measured from the file on disk, per the issue #148
  image-height rule; a missing image leaves `time_end` blank and dangles
  (`ASSET_MISSING`), and a present-but-unreadable image records a "time period
  unknown" warning — neither is a fail-fast.
- **FR-012**: Each demon row's band columns MUST carry the 0 – 40 Hz range read
  from `demon.glc`, so the generator derives a 0 – 40 Hz GramFrame frequency
  range with no special-casing.
- **FR-013**: `extract` MUST order the gram's demon row(s) **before** its Lofar
  rows; multiple demon rows MUST be ordered deterministically (marker-filename
  order).
- **FR-014**: A gram whose first-Lofar folder holds no `demon.glc` MUST produce
  exactly the rows it produced before this feature (no demon row, no change).
- **FR-015**: The demon row MUST NOT disturb the gram's existing analysis and
  Lofar rows or the one-topic-per-gram merge; `topic_type="demon"` is a new
  value alongside `analysis` and `glc`.

#### Generate (rendering)

- **FR-016**: The generator MUST emit each demon block as an inline image
  GramFrame table — the same block shape used for a Lofar image gram — carrying
  the demon image, its pixel-height time period, and the 0 – 40 Hz band.
- **FR-017**: The generator MUST place the demon block(s) after the
  analysis-sheet section and **before** all Lofar blocks in the topic body.
- **FR-018**: The demon block MUST be visible to **all** audiences (no
  instructor-only restriction); consequently in student editions, where the
  analysis section is filtered out, the demon block leads the page.
- **FR-019**: The generator MUST copy each demon image beside the topic under a
  stable bare filename (`demon.png`, `demon-2.png`, …) so every demon `href` is
  a bare filename with no `../` traversal, consistent with the
  self-contained-topic invariant.
- **FR-020**: A demon row whose image is absent on disk MUST dangle, not crash:
  the demon block is still emitted with its intended local `href` so dropping
  the image in and re-running resolves it without churning the XML.

#### Cross-stage / data

- **FR-021**: `topic_type="demon"` MUST participate in the CSV identity model so
  that the identity tuple `(publication, chapter, gram_id, topic_type,
  sequence)` remains unique for demon rows and the generator never silently
  merges two demons; a demon row's identity fields are validated as strictly as
  every other row's.
- **FR-022**: The dedupe stage MUST carry demon rows through unchanged (they
  ride with their gram's `gram_id` and renumbering) — a demon row is neither
  dropped nor renumbered independently of its gram.
- **FR-023**: A `demon_stock.png` test fixture (the sample attached to issue
  #151) MUST be available at the repository root for building synthetic demon
  test data, and the synthetic/mock corpus MUST be able to exercise the demon
  path end-to-end.
- **FR-024**: The demon filename's descriptive tokens — a duration reading
  (`10m2s`), a frequency reading (`0-40Hz`), and any leading duration prefix
  (`4m10s_`) — MUST be treated as decorative: neither parsed for values nor
  validated against the image or the fixed band. Time comes from pixel height
  (FR-011) and the band is the fixed 0 – 40 Hz (FR-005/FR-012).

### Key Entities

- **Demon image**: An author-delivered screenshot rendered by the alternate
  algorithm, carrying a `Demon` token — leading (`Demon - 10m2s 0-40Hz.png`,
  `Demon - 0-40Hz.png`) or after a duration prefix (`4m10s_Demon - 0 - 40 Hz.jpg`).
  Additive to a gram — never a `.wav` replacement.
- **`demon.glc` marker**: A per-demon GLC written into the source gram folder by
  `ingest`, cloned from the folder's first hyperlinked `.glc`, repointed at the
  demon image and carrying the fixed 0 – 40 Hz band. Its presence is the signal
  `extract` keys on. Named `demon.glc`, `demon-2.glc`, … when several exist.
- **Demon row**: A `topic_type="demon"` CSV row, one per marker, carrying the
  demon image path, pixel-height `time_end`, and 0 – 40 Hz band, ordered ahead of
  the gram's Lofar rows.
- **Demon block**: The leading inline GramFrame table the generator emits for a
  demon row — after the analysis section, before the Lofars, visible to all
  audiences.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a delivery containing demon images in matched gram folders, a
  single verify-then-`--apply` cycle seeds a `demon.glc` marker (and image copy)
  for 100% of them, with zero manual edits.
- **SC-002**: After apply and a fresh extract/generate cycle, every gram with a
  demon image renders a demon GramFrame as its first content block (after the
  instructor-only analysis section), with the frequency range shown as 0 – 40 Hz
  and the time period equal to the demon image's pixel height in seconds.
- **SC-003**: The demon GramFrame appears in the instructor, student-own, and
  student-other editions alike; in the student editions it is the first block on
  the page.
- **SC-004**: Grams with no demon image are byte-identical in extract output and
  generated topics to their pre-feature output — the feature is strictly
  additive.
- **SC-005**: Running `--apply` twice in a row produces zero additional changes
  on the second run; the second run reports every already-seeded demon as
  already present.
- **SC-006**: Two consecutive extract/generate/publish runs over an unchanged
  source (including a demon gram) yield byte-identical CSV, DITA, and HTML,
  preserving the determinism invariant.
- **SC-007**: A gram carrying more than one demon image renders each as its own
  leading GramFrame, in a stable order, ahead of the Lofars.

## Assumptions

The four core mechanics below were confirmed with the product owner; the
remainder are recorded defaults, open to veto on review.

**Confirmed:**

- The **0 – 40 Hz** constant is baked into `demon.glc`'s band settings by
  `ingest` (option: *ingest rewrites demon.glc bands*); `extract` and the
  generator read it through the ordinary band path with no demon special-case at
  render time.
- The demon image is copied into the source gram folder **keeping its original
  `Demon - …` filename**, and the cloned `demon.glc`'s `<filename>` is repointed
  to it (option: *keep original name + repoint glc*).
- The demon entry is a **new `topic_type="demon"`** CSV row, emitted by the
  generator after the analysis section and before the `sequence`-ordered Lofars
  (option: *new topic_type 'demon'*).
- `extract` looks for `demon.glc` in the **parent folder of the gram's first
  resolved Lofar `.glc`**, and a gram **may carry more than one** demon image
  (option: *first Lofar folder, allow multiple*).

**Recorded defaults (veto on review):**

- Multiple demon markers in one gram folder are named `demon.glc`, `demon-2.glc`,
  … in incoming-filename order, and render in that order.
- Marker creation and image copy happen only under `--apply`; default **verify**
  mode reports demon images in a read-only `DEMON IMAGES` section.
- Demon images may carry `.png`, `.jpg`, or `.jpeg` extensions (case-insensitive).
- The demon block is shown to all audiences — it is not instructor-gated like the
  analysis sheet.
- The demon filename's `10m2s` / `0-40Hz` tokens are decorative and are neither
  parsed nor validated; time comes from pixel height and the band is the fixed
  0 – 40 Hz.

**General (inherited from the pipeline constitution):**

- This is pre-CSV preparation: the operator re-runs `extract` after `--apply`,
  so no reconciliation with any in-flight signed-off CSV is needed.
- Missing demon assets dangle (they do not crash); the pipeline stays strict on
  its own identity data and forgiving at the external-asset boundary.
- Deterministic, idempotent output; air-gap-debuggable operation; stdlib-only
  tests; the existing Python 3.9 / WinPython runtime floor — detailed in the
  plan, not here.

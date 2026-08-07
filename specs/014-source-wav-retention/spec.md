# Feature Specification: Source Audio Retention

**Feature Branch**: `claude/dreamy-ramanujan-dj434q`
**Created**: 2026-08-07
**Status**: Draft
**Input**: User description: "The .wav file should be copied to the dita target. Eventually, the current source folder will be archived. But, the analyst may decide that he needs to produce a higher quality version of the PNG. So, he'll need to be able to open the .wav in the legacy spectrogram analysis tool, and take a new screenshot. The dita target folder will become the 'working' folder for these publications, so it's right that they continue to store the original .wav folders." Plus, on the `.wav.bak` rename: "how about using .back.wav, it will show it's a backup, but the o/s will still open it correctly." Subsequently corrected to: "use .bac , not .back".

## Overview

Two prep-time stages convert a live-render gram into a pre-rendered one:
`ingest_gram_images.py` imports a tree of author screenshots, and
`relink_glc_to_image.py` repoints a `.glc` at an image the author dropped in
beside it. Either way the `.glc` stops naming a `.wav` and starts naming an
image, and from that moment the generator treats the gram as an image gram —
so the originating audio never reaches `dita/`.

That was correct while `source/` was the permanent home of the corpus. It stops
being correct once **`dita/` becomes the working folder and `source/` is
archived**: an analyst who needs a better rendering of a gram must open the
original audio in the legacy spectrogram tool and take a fresh screenshot, and
the audio will no longer be anywhere they can reach.

This feature retains the source audio alongside the image it produced, on the
same principle as the analysis sheet's Word original (feature 013): the working
folder should carry what its deliverables were derived from.

Two things follow:

1. **The audio travels with the converted gram** — copied into the gram's topic
   folder beside the image, referenced by nothing.
2. **`relink` stops making the audio un-openable.** It currently moves the
   `.wav` aside to `<name>.wav.bak`, which both loses the file association (the
   OS will not hand a `.bak` to the spectrogram tool) and asserts the file is
   discardable. It becomes `<name>.bac.wav` — still marked as the superseded
   original, but still a `.wav` the analyst can double-click.

### `relink` appears never to have run

Both the committed corpus and the target show **no evidence of `relink` ever
having been used**: zero `.wav.bak` files, zero `Image <N>-…` candidate images,
and every `.wav` still unconverted. The author's deliveries go through
`ingest`'s parallel incoming tree.

Two consequences, both simplifications:

- **The pairing question is settled at no cost.** `relink` will name the
  retained audio after the **image's** stem, so both routes leave the image and
  its audio sharing one stem and a single probe finds it. The objection to that
  choice was that it discards the wav's original filename — but no file in
  existence carries that name, because the conversion has never happened. There
  is nothing to lose.
- **No migration is needed.** An earlier draft carried a third user story to
  rename existing `.wav.bak` files. There are none. It is dropped rather than
  built speculatively; the reasoning is recorded here in case one ever surfaces.

`relink`'s own behaviour is still corrected (US2) so that the route produces a
usable result if it is ever picked up again. Whether to retire the script
altogether is a **separate decision**, deliberately out of scope here.

### What this does *not* change

A gram whose `.glc` still names a `.wav` is untouched. Its audio is **already**
copied into the topic folder today, and referenced — the generator surfaces the
`.glc` as a viewer link and copies the `.glc`/`.wav` pair beside it. This
feature is only about grams that have already been **converted** to an image,
where the audio is currently dropped.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — The source audio travels with the converted gram (Priority: P1)

Months after handover, `source/` is archived and an analyst is asked to improve
a gram whose spectrogram is too coarse to read. They open the gram's folder in
the DITA tree and the originating `.wav` is sitting beside the image it
produced. They open it in the legacy spectrogram tool, take a better
screenshot, and drop it in.

**Why this priority**: This is the feature. Without it the archive is the only
copy, and the working folder cannot support the one task it exists for.

**Independent Test**: Convert a gram (either prep route), run the pipeline, and
confirm the gram's topic folder holds both the image and a byte-identical copy
of the originating audio, with the topic XML unchanged.

**Acceptance Scenarios**:

1. **Given** a gram converted by `ingest`, **When** the pipeline runs, **Then**
   the gram's topic folder contains the source audio beside its image, and the
   copy is byte-identical to the source file.
2. **Given** a gram converted by `relink`, **When** the pipeline runs, **Then**
   the same holds — the two prep routes produce the same outcome.
3. **Given** a gram with several converted Lofars, **When** the pipeline runs,
   **Then** each Lofar's own audio is copied under a name that pairs it with
   its image unambiguously.
4. **Given** any gram, **When** the pipeline runs, **Then** the topic XML is
   byte-identical to the previous release and the published output for every
   edition is unchanged — the audio is referenced by nothing.
5. **Given** a gram that was always image-backed (no audio ever existed),
   **When** the pipeline runs, **Then** no audio is copied and no warning is
   raised.
6. **Given** a gram whose `.glc` still names a `.wav`, **When** the pipeline
   runs, **Then** its behaviour is exactly as before — the audio is copied once,
   as the `.glc` viewer link's companion, not twice.

---

### User Story 2 — A retained original stays openable (Priority: P1)

An analyst finds the retained audio and double-clicks it. It opens in the
spectrogram tool, because it is still a `.wav`. Its name tells them it is the
superseded original rather than the gram's current asset.

**Why this priority**: P1 alongside US1 — a retained file the operating system
will not open does not satisfy the requirement. It also fixes the association
for `relink`-converted grams, without which US1 delivers an unusable file.

**Independent Test**: Run `relink` over a gram folder and confirm the retained
audio is named `<stem>.bac.wav`, with a `.wav` extension, and that no
`.wav.bak` is produced.

**Acceptance Scenarios**:

1. **Given** a `.wav`-backed `.glc` and a matching author image, **When**
   `relink` converts it, **Then** the audio is retained as `<stem>.bac.wav`
   and no `.wav.bak` is written.
2. **Given** the same conversion, **When** the retained file is inspected,
   **Then** its final extension is `.wav`, so the OS file association resolves
   to the spectrogram tool.
3. **Given** a folder `relink` has already converted, **When** `relink` runs
   again, **Then** nothing changes — the transform stays idempotent.

---

### Edge Cases

- **A gram that was always image-backed.** ~82% of the corpus. No audio exists,
  none is copied, and that is not a warning.
- **A still-`.wav`-backed gram.** Untouched: its audio already reaches the topic
  folder as the viewer link's companion. The feature must not copy it twice or
  under a second name.
- **The retained audio is missing at generate time.** Warn and continue, per the
  dangling-asset rule. Nothing references it, so there is no href to repair.
- **Two grams sharing one source recording.** Each topic folder gets its own
  copy. Feature 006's large-asset redirect operates on CSV rows, not parked
  assets, so it does not deduplicate these — a known cost, quantified in the
  extract summary rather than silently absorbed.
- **`--stub-wav` is in force.** The retained audio is stubbed like any other
  `.wav` copy, so the slim-tree-for-transit workflow keeps working.
- **The suppression flag is set.** No audio is copied; everything else is
  identical, and the run says how many files it skipped so the omission is
  visible rather than silent.
- **A `.wav.bak` turns up after all.** None exist today, which is why no
  migration is specced. If one surfaces, its audio is simply not retained — the
  probe finds no `.wav`/`.bac.wav` beside the image — and it is counted in
  FR-010's "without retained audio" figure rather than silently ignored. That
  visibility is the safety net; a migration can be added if the count is ever
  non-zero for that reason.

## Requirements *(mandatory)*

### Retaining the audio (US1)

- **FR-001**: Where a gram's Lofar was converted from audio to a pre-rendered
  image, the pipeline MUST copy the originating audio into the gram's topic
  folder.
- **FR-002**: The copy MUST take a stable name that pairs it unambiguously with
  the image it produced, following the existing per-gram asset convention
  (`lofar-N.png` → `lofar-N.wav`).
- **FR-003**: The topic XML MUST NOT reference the copied audio. Published
  output for every edition MUST be byte-identical to the release before this
  feature.
- **FR-004**: The path to the originating audio MUST be resolved at extraction
  and carried in the intermediate CSV, appended at the right edge so older CSVs
  read forward-compatibly.
- **FR-005**: A gram whose `.glc` still names a `.wav` MUST keep its current
  behaviour exactly — one copy, as the viewer link's companion.
- **FR-006**: Audio that is recorded but absent at copy time MUST warn and
  continue, never abort.
- **FR-007**: Copying MUST be deterministic — two runs over unchanged input
  produce byte- and timestamp-identical copies.
- **FR-008**: Retention MUST be **on by default**, with a flag to suppress it
  for a transfer where the audio is not needed. When suppressed, the run MUST
  report how many files it skipped.
- **FR-009**: An existing `--stub-wav` run MUST substitute the stub for the
  retained audio too, so the slim-tree workflow is unaffected.
- **FR-010**: The extraction summary MUST report how many converted Lofars have
  retained audio and how many do not, so the operator can see the coverage and
  the size implication before transferring the tree.

### Keeping it openable (US2)

- **FR-011**: `relink` MUST retain the converted `.wav` under a name ending in
  `.wav`, so the operating system's file association still resolves to the
  spectrogram tool. The name MUST also mark the file as the superseded
  original.
- **FR-012**: `relink` MUST NOT produce `.wav.bak` files.
- **FR-013**: `relink` MUST remain idempotent — a converted folder reconverted
  changes nothing.

### Key Entities

- **Source Audio**: The `.wav` a gram was originally rendered from live by the
  on-PC GLC viewer. After conversion it is no longer the gram's asset, but it
  is the only thing from which a better image can be produced.
- **Converted Lofar**: A Lofar whose `.glc` once named a `.wav` and now names a
  pre-rendered image. The subject of this feature.
- **Retained Original**: The source audio kept beside its image after
  conversion, named to show it is superseded while remaining openable.
- **Gram Topic Folder**: The per-gram output folder. Becomes the working folder
  once `source/` is archived, and so must carry the image, the analysis sheet's
  Word original (feature 013), and now the source audio.

## Success Criteria *(mandatory)*

- **SC-001**: 100% of converted Lofars whose source audio still exists have that
  audio available in the gram's own output folder.
- **SC-002**: An analyst can open a retained original directly from the working
  folder, in the spectrogram tool, without renaming it first.
- **SC-003**: The published output for every edition is byte-identical before
  and after this feature — no reader sees any change.
- **SC-004**: Zero retained originals require renaming before an analyst can
  open them in the spectrogram tool.
- **SC-005**: The operator can see, before transferring, how much audio the
  tree carries and can produce a tree without it in one flag.
- **SC-006**: Two consecutive pipeline runs over unchanged input produce
  identical output, retained audio included.

## Assumptions

- **The source audio sits in the gram folder alongside the image it produced.**
  `ingest` leaves it in place under the wav's own stem; `relink` retains it in
  the same folder. A recording stored elsewhere is out of scope.
- **The pairing is recorded at conversion time, not re-derived later.** `ingest`
  already names the imported image after the wav's stem, so the two share a
  stem. `relink` does not — its Pattern B maps `WAV 1.wav` to
  `Image 1-0-110 Hz.jpg` — so `relink` will name the retained audio after the
  image's stem, making the association hold by construction in both routes. This
  was an open trade-off while it implied discarding the wav's original filename;
  it is now free, because `relink` has never run and no file carries that name.
- **Real `.wav` files are substantial.** The committed corpus holds 844-byte
  stubs, so the true size impact cannot be measured here; the existence of
  `--stub-wav` and feature 006's 10 MiB redirect implies real audio is large.
  This is why FR-008 makes retention suppressible and FR-010 reports coverage.
- **The retained audio reaches `dita/` only, not the published HTML** — nothing
  references it, and unreferenced files are not carried into rendered output.
  Intended: analysts work in the DITA source.
- **`relink` is not a live delivery route.** No `.wav.bak` files and no
  `Image <N>-…` candidates exist in either tree, and the author delivers through
  `ingest`. `relink` is corrected rather than exercised; whether to retire it is
  a separate decision.

## Dependencies

- Builds on `relink_glc_to_image.py` and `ingest_gram_images.py` (the two
  conversion routes) and on feature 013's precedent for parking an unreferenced
  source asset beside a topic.
- **US2 should reach the corpus with or before US1**, so retained audio is
  openable from the moment it starts being copied.
- No new runtime dependency — file copying and renaming only.

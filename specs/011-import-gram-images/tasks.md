# Tasks: Import Author Gram Images

**Feature**: `specs/011-import-gram-images/` | **Branch**: `claude/gram-image-matching-metadata-365z6d`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests are included per the constitution's Test-First Discipline (Principle III):
every behaviour gets a stdlib `unittest` regression over synthetic `tempfile`
trees. Suite must be green before completion:
`python -m unittest discover tests/`.

Nearly everything lands in two new files (`scripts/ingest_gram_images.py`,
`tests/test_ingest_gram_images.py`), so parallelism within a story is limited
by design; `[P]` marks only genuinely different-file work.

## Phase 1: Setup

- [ ] T001 Confirm the reuse points import cleanly and unchanged: `parse_glc` from `scripts/extract_to_csv.py`; `rewrite_glc_filename`, `FILENAME_TAG_RE`, `setup_logging`, `IMAGE_EXTENSIONS` from `scripts/relink_glc_to_image.py` (sibling-import pattern both scripts already use). No behavioural edit to either existing script is in scope; if a helper proves un-importable as-is, duplicate it with a pointer comment per research R6 fallback.

## Phase 2: Foundational (blocking prerequisites)

Skeleton, parsing, and the per-gram view that every user story reads.

- [ ] T002 Create `scripts/ingest_gram_images.py`: module docstring (two-phase purpose; **explicit note of the deliberate wav-left-in-place divergence from `relink_glc_to_image.py`**), `from __future__ import annotations`, sibling-import block, dual logging to `ingest.log` (reuse `setup_logging`), argparse (`--incoming-root` required, `--source-root` required, `--apply` flag), root validation (missing/non-dir → error, exit 1), and the REPL-safe `sys.ps1` exit guard used by the other stages.
- [ ] T003 In `scripts/ingest_gram_images.py`, implement the filename parser: `CandidateImage` dataclass + `parse_image_filename(name)` — extension gate (`.jpg`/`.jpeg`/`.png`, case-insensitive, case preserved), leading token = chars before first space, token regex `^(\d+)m(?:(\d{1,2})s)?$` (case-insensitive) → `seconds = m*60 + s(0)`, stem = remainder stripped (empty stem ⇒ unparseable). Non-image files return `None` (debug log at call site).
- [ ] T004 In `scripts/ingest_gram_images.py`, implement `GramFolderView` (per data-model.md): scan the gram folder's `*.glc` in sorted order via `parse_glc`, bucket `GlcRef(glc_path, referenced_basename, has_crop)` into `wav_refs`/`image_refs` keyed by referenced-asset stem (extension-blind), collect `unreadable` for GLCs with no inner filename; `has_crop` = raw text contains `<bitmap_crop_values>`.
- [ ] T005 In `scripts/ingest_gram_images.py`, define the outcome taxonomy and `Tally` (one counter per class from data-model.md, plus `glcs_rewritten`/`images_copied`) and the `Outcome` record the report/tally aggregate.
- [ ] T006 Create `tests/test_ingest_gram_images.py`: tempfile tree-builder helpers (source doc with container/gram folders, minimal wav-backed and image-backed GLC text fixtures, incoming doc/gram/image builder) + foundational cases: duration table (`21m`→1260, `5m26s`→326, `0m`→0, `10M` accepted; `326`, `5:26`, `5m261s`, `5m26s.jpg`-style empty stem rejected), extension gating, `GramFolderView` bucketing (wav vs image refs, unreadable isolation, `has_crop` detection).

**Checkpoint**: parser + view proven; stories can build on them.

## Phase 3: User Story 1 — Verify the incoming tree against the source corpus (P1) 🎯 MVP

**Goal**: Read-only verify mode matches doc folders → container → gram folders
→ image stems vs GLC-referenced wavs, and writes `ingest_report.txt` with
nearest candidates, an unparseable-duration survey, trend grouping, and a
tally. Nothing on disk changes except the report and log (both in cwd).
**Independent test**: Synthetic trees with one exact match, one folder drift,
one stem drift, one unparseable prefix → each lands in its report class; both
trees byte-unchanged.

- [ ] T007 [US1] In `scripts/ingest_gram_images.py`, implement the tree walk: sorted iteration of incoming doc dirs → exact-name match against `--source-root` children (miss ⇒ `unmatched-doc`); container resolution as the single subdirectory of the matched source doc dir (0 or 2+ ⇒ `structurally-ambiguous-doc`, doc skipped); sorted incoming gram dirs → exact-name match against container children (miss ⇒ `unmatched-gram`).
- [ ] T008 [US1] In `scripts/ingest_gram_images.py`, implement per-gram image classification for verify: each eligible incoming file through `parse_image_filename` (`unparseable-duration` with raw token echoed) then stem lookup in the `GramFolderView` — wav-stem hit ⇒ `matched` (carrying all `GlcRef`s sharing the stem), no hit ⇒ `unmatched-image` with the folder's available wav stems echoed. (Ambiguous / already-converted refinement lands in US3; classify them as matched/unmatched here without special casing.)
- [ ] T009 [US1] In `scripts/ingest_gram_images.py`, implement suggestions + trends: `difflib.get_close_matches(name, candidates, n=3, cutoff=0.6)` for `unmatched-doc`/`unmatched-gram`/`unmatched-image`; drift label per research R4 probe order (`case-only`, `whitespace-only`, `case+whitespace`, `token-drift('X' → 'Y')`, `other`) against the top candidate; aggregate identical token-drift pairs with counts for the TRENDS section.
- [ ] T010 [US1] In `scripts/ingest_gram_images.py`, implement the report writer per contracts/ingest-contract.md: `ingest_report.txt` in cwd, header (roots + mode), one section per non-empty outcome class with path-sorted entries, TRENDS, SUMMARY footer mirroring the console summary; no timestamps in the body. Wire `main()` end-to-end for verify mode (report + log + console tally).
- [ ] T011 [P] [US1] In `tests/test_ingest_gram_images.py`, add US1 cases: exact match tallied; folder drift → `unmatched-gram` with candidate + correct drift label; doc drift → `unmatched-doc`; container 0 and 2 subdirs → `structurally-ambiguous-doc` and doc skipped; unparseable survey lists raw tokens; `unmatched-image` echoes available wav stems; token-drift trend aggregation counts; report determinism (two identical runs ⇒ byte-identical report); read-only guarantee (full tree snapshot before/after verify is identical, source *and* incoming).

**Checkpoint**: verify/report loop usable on its own — the operator can start
fixing the incoming delivery with just this.

## Phase 4: User Story 2 — Apply the conversion to verified matches (P2)

**Goal**: `--apply` copies each matched image beside its GLC(s) under the wav
stem, rewrites `<filename>`, inserts `<bitmap_crop_values><bottom_crop>N
</bottom_crop></bitmap_crop_values>`, leaves the wav untouched, and is
idempotent.
**Independent test**: Synthetic matched pair → copy present, GLC diff is
exactly the filename change + crop block, wav byte-identical, re-run no-op.

- [ ] T012 [US2] In `scripts/ingest_gram_images.py`, implement the GLC edit: one in-memory pass that (a) rewrites the first `<filename>` inner text to the target basename (reuse `FILENAME_TAG_RE`/`rewrite_glc_filename` mechanics) and (b) inserts the `bitmap_crop_values` block immediately after `</filename>`, inferring per-level indentation from the `<filename>` line (default two spaces) per research R6; single `write_text` only if both anchors found, else per-file error → skip + count, no write.
- [ ] T013 [US2] In `scripts/ingest_gram_images.py`, implement apply orchestration: for each `matched` outcome in sorted gram-folder order — `shutil.copyfile` the incoming image to `<gram>/<wav-stem><incoming-ext>` (unconditional overwrite, extension case preserved), apply the T012 edit to every `GlcRef` sharing the wav stem (sorted), bump `images_copied`/`glcs_rewritten`; wav never touched. Verify-mode outcome list is reused — apply is verify + mutation, one code path for matching.
- [ ] T014 [US2] In `scripts/ingest_gram_images.py`, classify `already-converted`: an incoming stem hitting `image_refs` (not `wav_refs`) lands in the `already-converted` info class in both modes — this is the idempotency rule that keeps post-apply verifies and re-applies clean and silent-by-default.
- [ ] T015 [P] [US2] In `tests/test_ingest_gram_images.py`, add US2 cases: copy bytes equal incoming image and stale copy overwritten; rewritten GLC text differs from original **only** by the `<filename>` inner text and the inserted crop block (position after `</filename>`, indentation, `<bottom_crop>326</bottom_crop>` value); `parse_glc` on the rewritten file yields `image_filename == "WAV 1.jpg"` and `time_end == "326"` (downstream contract); two GLCs referencing one wav → one copy, both rewritten; wav byte-identical after apply; second apply run changes nothing (tree snapshot identical) and tallies `already-converted`; verify run after apply is clean.

**Checkpoint**: full convert path done; US1+US2 = the working tool.

## Phase 5: User Story 3 — Ambiguities warn and defer, never guess (P3)

**Goal**: Ambiguous, unreadable, and already-cropped cases skip with warnings
and are counted; the closing summary enumerates every outcome class.
**Independent test**: Two images claiming one wav → none applied, warning
names both, summary counts one ambiguous.

- [ ] T016 [US3] In `scripts/ingest_gram_images.py`, implement `ambiguous`: two+ parsed incoming images in one gram folder resolving to the same wav stem ⇒ none matched/applied, warning + report entry listing every claimant.
- [ ] T017 [US3] In `scripts/ingest_gram_images.py`, implement the GLC guard classes: `glc-unreadable` (excluded from matching, folder's other GLCs still process — already bucketed by T004, surface as warning + count) and `glc-already-cropped` (a matched wav-backed `GlcRef` with `has_crop` ⇒ that file skipped whole, warning, never double-inserted; other GLCs in the same match still rewritten).
- [ ] T018 [US3] In `scripts/ingest_gram_images.py`, finalise the summary: console + log + report SUMMARY line enumerating every outcome class count plus `glcs_rewritten`/`images_copied` (apply), matching data-model.md's Tally.
- [ ] T019 [P] [US3] In `tests/test_ingest_gram_images.py`, add US3 cases: ambiguous pair → nothing applied, warning lists both files, count = 1; already-cropped wav-backed GLC byte-untouched while a sibling GLC in the same match is rewritten; unreadable GLC isolated (other GLC in folder converts); summary counts assert across a mixed-outcome tree in both modes.

**Checkpoint**: all spec outcome classes implemented and counted.

## Phase 6: Polish & Cross-Cutting

- [ ] T020 Create the root wrapper `ingest.py` mirroring `relink.py`'s shape: docstring (REPL usage, verify-then-apply workflow, wav-divergence note), Config block (`INCOMING`, `SOURCE`, commented-out `"--apply"` toggle), pylib/scripts `sys.path` setup, module-cache pop including `ingest_gram_images`, `sys.argv` + `runpy.run_path`. Also add `"ingest_gram_images"` to the shared module-pop list in the existing root wrappers (`extract.py`, `introspect.py`, `dedupe.py`, `write.py`, `publish.py`, `snapshot.py`, `relink.py`, `pipeline.py`) for REPL-freshness consistency.
- [ ] T021 [P] Update `README.md`: wrapper table / target-layout tree / "Running on the air-gapped target machine" gain `ingest.py` beside `relink.py` in the prep group, with the verify→fix→apply loop and the honest note that ingest leaves the `.wav` in place where relink moves it aside (Principle VI).
- [ ] T022 [P] Update `CLAUDE.md`: cold-start wrapper sequence gains the `ingest.py` line; the relink line notes the sibling flow and the wav-disposition divergence.
- [ ] T023 Confirm packaging needs no change (research R8): `.github/scripts/package_release.py` globs pick up `ingest.py` under `wrappers/` and `ingest_gram_images.py` under `scripts/` — spot-check with a local `collect_entries()` run or the packager's own test if present.
- [ ] T024 Run the full gate: `python -m unittest discover tests/` green; quickstart walk (synthetic incoming vs in-repo `source/` copy: verify report classes → apply → `git diff` shows only filename+crop GLC edits and the copied image → re-apply no-op → `extract_to_csv.py` row carries `time_end`); revert the scratch mutation afterwards (work on a copy, keep `source/` pristine).

## Dependencies & Execution Order

- **Phase 1 → Phase 2**: T001 informs T002's import block. Within Phase 2,
  T002 → T003/T004/T005 (same file, sequential); T006 follows T003+T004.
- **US1 (T007–T011)** needs Phase 2. T007 → T008 → T009 → T010 sequential
  (same file, layered); T011 parallel with nothing (same test file as T006 but
  after T010 to assert end-to-end).
- **US2 (T012–T015)** needs US1's T007/T008 walk (apply reuses the verify
  matching path). T012 → T013 → T014; T015 after.
- **US3 (T016–T019)** needs US1 matching + US2's apply for its skip
  behaviours. T016/T017 → T018; T019 after.
- **Phase 6** last; T021/T022 are `[P]` (different files); T024 is the final
  gate.

## Implementation Strategy

- **MVP = Phases 1–3**: the verify/report loop alone lets the operator start
  triaging the real delivery (the fix-up loop is days of human work that can
  begin before apply exists).
- **Increment 2 = US2**: the conversion itself.
- **Increment 3 = US3 + Polish**: hardening, wrapper, docs, final gate.
- One new canonical script + one wrapper; zero edits to existing stages'
  behaviour (only the wrappers' module-pop lists and docs). Determinism checks
  ride in T011 (report) and T015 (re-apply no-op).

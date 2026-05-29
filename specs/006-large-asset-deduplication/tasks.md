# Tasks: Large Asset Deduplication with Reversible Provenance

**Input**: Design documents from `/specs/006-large-asset-deduplication/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are INCLUDED — the plan's Testing section explicitly names new
modules (`tests/test_deduplicate_csv.py`, `tests/test_rehydrate_dita.py`),
extensions to `tests/test_generate_dita.py`, and a 2-publication HTML fixture in
`tests/web/`. The project's air-gapped contract (CLAUDE.md) makes the
stdlib-`unittest` suite the canonical verification surface.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story. All paths are repository-root relative
(flat-script layout per features 001–005).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Each task names the exact file path it touches

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the new script skeletons and shared test fixtures the
later phases build on. No behaviour change yet.

- [X] T001 Create `deduplicate_csv.py` skeleton at repo root following the
  `verb_noun.py` / `main(argv) -> int` + `argparse` + `setup_logging(Path("dedup.log"))`
  pattern of `generate_dita.py` and `extract_to_csv.py` (`from __future__ import annotations`,
  stdlib-only, Python 3.9 floor). Wire `--csv`, `--image-root`, `--out`,
  `--threshold-bytes` (default `10 * 1024 * 1024`) per `contracts/dedup-cli.md`; leave
  the detection body as a documented TODO returning exit 0.
- [X] T002 Create `rehydrate_dita.py` skeleton at repo root with the same
  CLI/logging shape (`setup_logging(Path("rehydrate.log"))`); wire `--dita`,
  `--gram`, `--dry-run` per `contracts/dedup-cli.md`; leave the walk body as a
  documented TODO returning exit 0.
- [X] T003 [P] Add a shared dedup test fixture under `tests/fixtures/`: a CSV
  (`dedup_source.csv`, UTF-8-sig/CRLF/QUOTE_MINIMAL, full `CSV_COLUMNS` header)
  in which (a) one large `.wav`/`.glc` audio asset is referenced by ≥3 grams
  with byte-identical content and `file_size` > 10 MiB, (b) one large image is
  duplicated across ≥2 grams, and (c) at least one unique large asset and one
  small (≤10 MiB) duplicated asset that must stay untouched — plus the backing
  asset files those `png_path`/`glc_path` cells resolve to (small synthetic
  files whose recorded `file_size` is forced > threshold for the dedup-candidate
  rows). Document in a fixture README comment which rows are expected masters vs
  redirects.

**Checkpoint**: New scripts importable and runnable as no-ops; shared fixture in
place for all three stories' tests.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one piece every story leans on — the canonical "what does a
redirected lofar look like" agreement between the generator (writer) and
rehydrate (reader). Pinning the `<data>` element shape and the master-link href
convention here prevents US1 and US2 from drifting.

**⚠️ CRITICAL**: Complete before US1/US2 implementation so the provenance shape
is fixed once.

- [X] T004 In `generate_dita.py`, add module-level constants/helpers for the
  provenance contract: the `<data>` element name literal
  `ORIGINAL_ASSET_PATH = "original-asset-path"` and a small helper
  `_append_provenance_data(section, original_path)` that appends
  `<data name="original-asset-path" value="…"/>` as the **last** child of a lofar
  `<section>` (per `contracts/dita-provenance-data.md`). No caller yet — pure
  addition, keeps US1/US2 referencing one definition.
- [X] T005 In `generate_dita.py`, add the `MasterTarget` dataclass and an empty
  `master_index: dict[str, MasterTarget]` builder stub (`topic_dir`,
  `link_basename`) per data-model.md Entity 3, with docstring stating the
  population rule (record every non-redirected asset-owning row's `png_path`).
  No wiring into `main` yet.

**Checkpoint**: Provenance element shape and master-index type are defined and
referenced by name; user-story work can proceed without re-deciding them.

---

## Phase 3: User Story 1 - Shrink the published set by redirecting duplicates (Priority: P1) 🎯 MVP

**Goal**: A row carrying a resolvable `master_png_path` links its lofar to the
single master copy instead of copying its own asset; the master binary is
written exactly once; each redirected lofar carries the `<data>` provenance
element; a CSV without the column is byte-for-byte inert.

**Independent Test**: Hand-craft a CSV where a large asset referenced by several
grams nominates the first as master and redirects the rest, run
`generate_dita.py`, and confirm the master asset exists once, every redirected
gram links to it via a `../` href, the `<data>` element is present on each
redirected lofar only, and an un-redirected CSV produces identical output.

### Tests for User Story 1 (write first, ensure they FAIL) ⚠️

- [X] T006 [P] [US1] In `tests/test_generate_dita.py`, add `test_inert_when_master_column_absent`:
  generate from a CSV lacking `master_png_path` (the existing `minimal.csv`) and
  assert output is byte-identical to a baseline run — `<data>` absent everywhere,
  every asset copied locally (FR-010, SC-005).
- [X] T007 [P] [US1] In `tests/test_generate_dita.py`, add
  `test_redirected_image_href_points_to_master`: from a CSV where gram B's image
  row redirects to gram A's `png_path`, assert gram B's `<image href>` is the
  POSIX `../`-relative path to gram A's copy and **no** image file was written
  into gram B's folder (FR-004).
- [X] T008 [P] [US1] In `tests/test_generate_dita.py`, add
  `test_redirected_audio_links_master_glc`: from a CSV where a `.wav` row
  redirects, assert the redirected lofar's `<xref>` targets the master `.glc`
  via `../`, and neither `.glc` nor `.wav` was copied into the redirected gram;
  the master gram holds both `.glc` and `.wav` side by side (FR-009).
- [X] T009 [P] [US1] In `tests/test_generate_dita.py`, add
  `test_master_binary_written_exactly_once`: with N grams redirecting to one
  master, assert exactly one physical copy of the asset exists across the whole
  `--out` tree (SC-001).
- [X] T010 [P] [US1] In `tests/test_generate_dita.py`, add
  `test_provenance_data_emitted_on_redirected_lofar_only`: assert each redirected
  lofar `<section>` has exactly one `<data name="original-asset-path">` whose
  `@value` is the link target's original local path (the row's `png_path` for an
  image lofar, the row's `glc_path` for an audio lofar — never the `.wav`), and
  that non-redirected lofars carry none (FR-006, FR-007).
- [X] T011 [P] [US1] In `tests/test_generate_dita.py`, add
  `test_blank_or_unresolvable_master_falls_back_with_warning`: a row whose
  `master_png_path` is blank-but-present or names a non-existent master is
  emitted as a normal local-copy lofar (no `<data>`), and a WARNING is logged
  (FR-014); generation still exits 0.
- [X] T012 [P] [US1] In `tests/test_generate_dita.py`, add
  `test_dedup_export_idempotent`: two consecutive runs over the same redirecting
  CSV produce byte- and stat-identical output (`filecmp.dircmp` deep compare),
  matching the existing idempotency contract (FR-013, SC-006).

### Implementation for User Story 1

- [X] T013 [US1] In `generate_dita.py` `read_csv`, read `master_png_path` as an
  optional cell: add it to `OPTIONAL_CSV_COLUMNS` (documentation only) and ensure
  every row dict resolves `row.get("master_png_path", "")` — do **not** add it to
  the strict `CSV_COLUMNS` required-set, preserving inert-by-default validation
  (FR-010, R7).
- [X] T014 [US1] In `generate_dita.py`, implement the **index pass**: before the
  per-gram emit loop in `main`, walk all rows in deterministic order and populate
  `master_index` mapping each non-redirected asset-owning row's `png_path` →
  `MasterTarget(topic_dir, link_basename)` — image rows key on the slugified
  image basename, `.wav` rows on the slugified **`.glc`** basename (FR-009,
  data-model.md Entity 3, R4). Compute `topic_dir`/suffix exactly as the emit
  pass does (`_topic_dir_for_row`, `_suffix_for_row`) so locations agree.
- [X] T015 [US1] In `generate_dita.py` `emit_gram_topic` (and its callees), thread
  the `master_index` through and implement the **redirect branch** for image
  lofars: when the row's `master_png_path` resolves in the index, skip
  `copy_asset`, compute the href as `os.path.relpath(master.topic_dir /
  master.link_basename, this topic_dir)` POSIX-separated (reuse
  `resolve_image_href`'s relpath logic), pass that href into
  `_append_gramframe_table`, and call `_append_provenance_data(section, row["png_path"])`
  (FR-004, FR-005, FR-006).
- [X] T016 [US1] In `generate_dita.py`, implement the **redirect branch** for
  audio (`.wav`) lofars in `emit_gram_topic`: when redirected, skip copying both
  `.glc` and `.wav`, compute the `../` href to the master `.glc`
  (`master.link_basename`), pass it into `_append_glc_viewer_link`, and call
  `_append_provenance_data(section, row["glc_path"])` (FR-009, R5). Ensure the
  master row itself still copies both files locally (it is non-redirected).
- [X] T017 [US1] In `generate_dita.py`, add the blank/unresolvable-master guard:
  if `master_png_path` is non-empty but not found in `master_index` (missing
  master, blank-after-strip), log a WARNING and fall through to the normal
  local-copy path with no `<data>` (FR-014). Count redirected lofars and log the
  total in the generation summary (Observability per plan Constitution Check).
- [X] T018 [US1] Run `python -m unittest tests.test_generate_dita` and confirm
  T006–T012 pass; fix any determinism/href regressions until the existing
  suite plus the new tests are green.

**Checkpoint**: MVP complete — deduplicated export works end-to-end from a
post-processed CSV, inert by default, idempotent, with provenance recorded.

---

## Phase 4: User Story 2 - Understand and reverse the redirection later (Priority: P2)

**Goal**: `rehydrate_dita.py` consumes a redirected lofar (using only the DITA
content) and restores a self-contained gram — master (and, for a pair, its
adjacent `.wav`) copied back under the local slug, href re-localised, `<data>`
removed — yielding a topic indistinguishable from a never-deduplicated one.

**Independent Test**: Take a US1-deduplicated export, run `rehydrate_dita.py
--gram gram-NN`, and confirm the restored topic + assets match a baseline
(never-deduplicated) export of the same gram; running it again is a no-op.

### Tests for User Story 2 (write first, ensure they FAIL) ⚠️

- [X] T019 [P] [US2] Create `tests/test_rehydrate_dita.py` with a helper that
  produces a baseline (no-dedup) export and a deduplicated export from the same
  fixture CSV (reusing `generate_dita`), so tests can diff restored-vs-baseline.
- [X] T020 [P] [US2] In `tests/test_rehydrate_dita.py`, add
  `test_restored_image_topic_matches_baseline`: rehydrate a redirected **image**
  gram and assert its topic XML and local asset are byte-identical to the
  baseline gram (`<data>` gone, href re-localised, image copied back under the
  slug from `slugify_asset_name(basename(@value))`) — SC-004.
- [X] T021 [P] [US2] In `tests/test_rehydrate_dita.py`, add
  `test_restored_audio_pair_matches_baseline`: rehydrate a redirected **audio**
  gram and assert both the `.glc` (from `@value`) and its adjacent master `.wav`
  (restored by adjacency) are copied back under their slugs and the `<xref>` is
  re-localised — the pair matches baseline (FR-009, FR-012).
- [X] T022 [P] [US2] In `tests/test_rehydrate_dita.py`, add
  `test_noop_on_unredirected_lofar`: a lofar with no `<data name="original-asset-path">`
  is left untouched, and a second `rehydrate_dita.py` run over an already-restored
  tree changes nothing (idempotent no-op).
- [X] T023 [P] [US2] In `tests/test_rehydrate_dita.py`, add
  `test_dry_run_writes_nothing` and `test_missing_master_warns_but_relocalises`:
  `--dry-run` reports intended changes but writes no files (exit 0); a missing
  master file logs a WARNING yet still re-localises the href so a later drop-in
  resolves it (per `contracts/dedup-cli.md`).

### Implementation for User Story 2

- [X] T024 [US2] In `rehydrate_dita.py`, implement the DITA walk: enumerate
  `*.dita` topics under `--dita` (filtered by `--gram` when given), parse with
  `xml.etree.ElementTree`, and find lofar `<section>`s containing
  `<data name="original-asset-path" value="P">`. Reuse the generator's
  serialisation contract (LF, UTF-8 no BOM, `_pretty_indent`/`_serialise`-equivalent)
  so restored topics are byte-comparable to a generated one.
- [X] T025 [US2] In `rehydrate_dita.py`, implement the inverse transform for a
  redirected lofar: resolve the master file from the section's `<image>`/`<xref>`
  href (relative to the topic folder); recompute the local slug from
  `basename(P)` via `slugify_asset_name`; copy the master link target into the
  gram folder under that slug (`copy2` to preserve mtime/idempotency); rewrite the
  href to the bare local filename; and remove the `<data>` element (FR-008,
  FR-012, R6). Import the slug/copy helpers from `generate_dita` to avoid drift.
- [X] T026 [US2] In `rehydrate_dita.py`, add the audio-pair adjacency restore:
  when `P` is a `.glc`, also copy the master `.glc`'s **sibling** `.wav` (located
  beside the master `.glc` via the resolved href) back into the gram folder under
  the `.wav`'s own slug, so the on-PC GLC viewer's adjacency lookup resolves after
  rehydration (FR-009).
- [X] T027 [US2] In `rehydrate_dita.py`, wire `--dry-run` (compute and log
  intended copies/href-rewrites/`<data>` removals without writing) and the
  per-lofar logging + missing-master WARNING (re-localise anyway); ensure no-op on
  lofars without the element. Exit 0 on success and on `--dry-run`.
- [X] T028 [US2] Run `python -m unittest tests.test_rehydrate_dita` and confirm
  T020–T023 pass; iterate until restored topics match baseline byte-for-byte.

**Checkpoint**: A deduplicated gram can be fully reversed from the DITA alone;
US1 and US2 together close the round-trip.

---

## Phase 5: User Story 3 - Apply deduplication as an optional post-processing step (Priority: P3)

**Goal**: `deduplicate_csv.py` detects large (>10 MiB) content-duplicate assets,
nominates the first occurrence as master, and writes a copy of the CSV with
`master_png_path` populated — leaving small/unique assets untouched and
preserving the CSV file-level contract. An un-processed CSV stays inert (already
guaranteed by US1).

**Independent Test**: Run `deduplicate_csv.py` over the fixture CSV and confirm
only >threshold genuine duplicates are redirected (master row empty, duplicates
carry the master's `png_path`), small/unique large assets are left empty, and a
second run yields a byte-identical CSV.

### Tests for User Story 3 (write first, ensure they FAIL) ⚠️

- [X] T029 [P] [US3] Create `tests/test_deduplicate_csv.py` with a helper that
  runs `deduplicate_csv.main([...])` against the `tests/fixtures/dedup_source.csv`
  fixture and re-reads the output CSV.
- [X] T030 [P] [US3] In `tests/test_deduplicate_csv.py`, add
  `test_strict_threshold`: assets with `file_size` ≤ threshold are never
  redirected even when duplicated; only strictly-greater rows are candidates
  (FR-003); add a sub-case overriding `--threshold-bytes`.
- [X] T031 [P] [US3] In `tests/test_deduplicate_csv.py`, add
  `test_first_occurrence_is_master`: within a ≥2 content-identical group, the
  first row in row-identity order `(publication, chapter, gram_id, topic_type,
  sequence)` keeps an empty `master_png_path`; every other member's
  `master_png_path` equals the master's `png_path` (FR-002).
- [X] T032 [P] [US3] In `tests/test_deduplicate_csv.py`, add
  `test_unique_large_untouched` and `test_size_collision_confirmed_by_hash`:
  a unique large asset is never redirected; two same-`file_size` but
  byte-different files are **not** grouped (sha256 confirmation), while
  byte-identical ones are.
- [X] T033 [P] [US3] In `tests/test_deduplicate_csv.py`, add
  `test_missing_asset_left_unredirected_with_warning`: a candidate whose backing
  file is absent/unhashable is left non-redirected with a WARNING, exit 0
  (FR-014).
- [X] T034 [P] [US3] In `tests/test_deduplicate_csv.py`, add
  `test_csv_roundtrip_and_idempotent`: output preserves utf-8-sig / `,` /
  QUOTE_MINIMAL / `\r\n` / header, `master_png_path` is appended at the right
  edge, and a second run over the same inputs produces a byte-identical CSV
  (FR-013, SC-006); also assert non-identity author columns are unchanged.

### Implementation for User Story 3

- [X] T035 [US3] In `deduplicate_csv.py`, implement CSV I/O preserving the
  file-level contract: read with `utf-8-sig`/`csv.DictReader`, write with the
  same dialect the rest of the pipeline uses (UTF-8-with-BOM, `\r\n`,
  `QUOTE_MINIMAL`), appending `master_png_path` at the right edge if absent or
  repopulating it if present (contracts/csv-master-png-path.md §Invariants).
- [X] T036 [US3] In `deduplicate_csv.py`, implement candidate detection: a row is
  a candidate iff `int(file_size)` parses and is strictly `> --threshold-bytes`
  (default `10*1024*1024`). Group candidates by `file_size` first; only within a
  size-collision group of ≥2 confirm content identity via `hashlib.sha256` of
  `image_root / png_path` (a unique-size file is never hashed — perf note R1/plan).
- [X] T037 [US3] In `deduplicate_csv.py`, implement master nomination + redirect:
  sort each confirmed ≥2 group by the row-identity tuple, leave the first
  occurrence's `master_png_path` empty (master), set every other member's
  `master_png_path` to the master's `png_path` (FR-002). Leave single-member
  groups and non-candidates empty.
- [X] T038 [US3] In `deduplicate_csv.py`, add logging/exit per
  `contracts/dedup-cli.md`: per-group master path + redirect count + bytes
  reclaimed, a total reclaimed-bytes summary, WARNING for unhashable assets, exit
  0 including the "no duplicates found" case (output = input plus an empty
  column).
- [X] T039 [US3] Run `python -m unittest tests.test_deduplicate_csv` and confirm
  T030–T034 pass; iterate until green.

**Checkpoint**: The full pipeline works — `deduplicate_csv.py` → `generate_dita.py`
(dedup export) → `rehydrate_dita.py` (reverse) — each story independently testable.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, the HTML-publish verification spike, and the
end-to-end quickstart validation that ties the success criteria together.

- [X] T040 [P] Update `specs/001-pptx-dita-migration/contracts/csv-schema.md`:
  add a row documenting the optional right-edge `master_png_path` column with the
  backward-compat note (plan §Source Code).
- [X] T041 [P] Update `specs/001-pptx-dita-migration/contracts/dita-topic-schema.md`:
  document the `<data name="original-asset-path">` element on a redirected lofar
  `<section>` and the redirected `../` href shape (plan §Source Code).
- [X] T042 [P] Update `README.md` (and the column reference) to mention
  `deduplicate_csv.py` / `rehydrate_dita.py` in the pipeline overview and the new
  optional CSV column, consistent with how prior optional columns are documented.
- [ ] T043 (DEFERRED — requires DITA-OT + a publish_html.py run on an internet-connected dev host; the source-tree guarantees it verifies are covered by the unittests) Verify the DITA-OT HTML spike (research R3, FR-011): add a Jest test
  (and a small 2-publication fixture) under `tests/web/` asserting a redirected
  **cross-map/cross-publication** href resolves and renders/plays in the built
  `html/` tree and the master asset is referenced once. If it fails, apply the
  documented fallback in `publish_html.py` (stage shared masters per-map at
  publish time) and re-verify. Requires a prior `publish_html.py` run.
- [X] T044 Run the full canonical suite `python -m unittest discover tests/` and
  confirm all five scripts plus the new modules are green and deterministic
  (no regressions in features 001–005 tests).
- [X] T045 Execute the quickstart end-to-end (`specs/006-large-asset-deduplication/quickstart.md`
  steps 0–6) against the fixture/`mock` corpus and confirm SC-001…SC-006
  (one physical copy + smaller set, inert baseline, provenance count = redirect
  count, rehydration matches baseline, both exports idempotent).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup; pins the provenance/`<data>`
  shape and master-index type that US1 and US2 share. BLOCKS US1/US2 detail work.
- **User Story 1 (Phase 3)**: Depends on Foundational. The MVP — deliverable on
  its own with a hand-crafted redirecting CSV.
- **User Story 2 (Phase 4)**: Depends on Foundational; consumes the `<data>`
  shape US1 emits. Its tests reuse US1's generator to build a deduplicated tree,
  so practically sequence it after US1, though the rehydrate code only depends on
  the Phase-2 element contract.
- **User Story 3 (Phase 5)**: Depends on Setup (the CSV fixture). Independent of
  US1/US2 *code* — it only produces the column US1 consumes — so it can run in
  parallel with US1/US2 if staffed separately.
- **Polish (Phase 6)**: Depends on US1–US3 (T044/T045) except the doc tasks
  (T040–T042), which can start once the contracts are stable.

### User Story Dependencies

- **US1 (P1)**: Foundation only — no dependency on US2/US3.
- **US2 (P2)**: Element-shape dependency on Foundation; test setup leans on US1's
  generator output.
- **US3 (P3)**: Independent; feeds US1 at runtime but shares no code path.

### Within Each User Story

- Tests are written first and must FAIL before implementation.
- US1: read → index pass → emit redirect branches → guard/logging.
- US2: walk → inverse transform → audio adjacency → dry-run/logging.
- US3: CSV I/O → detection → nomination → logging.

### Parallel Opportunities

- T003 (fixture) is `[P]` against T001/T002 (different files).
- All test-authoring tasks within a story (T006–T012, T020–T023, T030–T034) are
  `[P]` — they add independent methods/files.
- US3 (Phase 5) can run fully parallel to US1/US2 with separate developers.
- Polish doc tasks T040–T042 are mutually `[P]`.

---

## Parallel Example: User Story 1

```bash
# Author all US1 tests together (independent assertions in one module):
Task: "test_inert_when_master_column_absent in tests/test_generate_dita.py"
Task: "test_redirected_image_href_points_to_master in tests/test_generate_dita.py"
Task: "test_redirected_audio_links_master_glc in tests/test_generate_dita.py"
Task: "test_master_binary_written_exactly_once in tests/test_generate_dita.py"
Task: "test_provenance_data_emitted_on_redirected_lofar_only in tests/test_generate_dita.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1.
2. STOP and validate: deduplicated export from a redirecting CSV, inert by
   default, idempotent, provenance recorded.
3. This alone delivers the headline size win (SC-001).

### Incremental Delivery

1. Setup + Foundational → ready.
2. US1 → test → demo (MVP: shrink the set).
3. US2 → test → demo (reversible/rehydrate).
4. US3 → test → demo (opt-in post-processor that produces the column).
5. Polish: docs, HTML spike, quickstart validation.

---

## Notes

- `[P]` tasks = different files / independent methods, no ordering dependency.
- Reuse `generate_dita` helpers (`slugify_asset_name`, copy/serialise) from
  `rehydrate_dita.py` and the index pass to keep slug/folder logic single-sourced
  (avoids drift, R2/R4).
- Preserve every existing invariant: determinism/idempotency, one runtime
  dependency, Python 3.9 floor, dangling-asset tolerance, dual logging
  (CLAUDE.md).
- Commit after each task or logical group; verify tests fail before implementing.

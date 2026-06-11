# Implementation Plan: Analysis-Sheet Images (render Word analysis sheets to PNG)

**Branch**: `claude/brave-gauss-CIG8Z` (developed on the existing working branch; no separate feature branch) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-analysis-sheet-images/spec.md`

## Summary

Make every gram's analysis table show **inline** in the topic — the fast,
intuitive experience the PNG-backed grams already give — by rendering the
analysis sheet's single landscape page to a PNG ahead of time, instead of
leaving a click-to-open link that launches MS Word mid-lesson.

The mechanism is a new **prep-time, single-purpose script**
`snapshot_analysis_docs.py` that scans the content tree for analysis
documents — selected by the corpus naming convention **`*analysis*` + `.doc`/
`.docx`** (analysis sheets sit in the **chapter folder alongside PPT source data
and other Word files**, so it must not render every Word doc it finds; see
research R7) — and for each renders a sibling PNG (`aaa_analysis.doc` →
`aaa_analysis.png`) via an external, configurable renderer (LibreOffice headless
by default). It renders the first page and **detects multi-page documents**,
warning rather than silently truncating (research R3). It is **render-once and
idempotent**: a sheet that already has its PNG is skipped, so the produced image
becomes a committed source asset and the renderer never runs inside a re-runnable
generate/publish loop.

Because the renderer produces a same-stem sibling, the only code change in the
pipeline proper is a **small tweak to `extract_to_csv.py`**: when an analysis
hyperlink targets a `.doc`/`.docx`, the analysis row's `png_path` is redirected
to the rendered sibling `.png` (with a warning recorded if that PNG is absent).
From there everything is unchanged — `generate_dita.py` already embeds a `.png`
analysis asset inline (`_append_analysis_section`, line 646) and dangles a
missing one per the existing missing-asset invariant, so **the generator and the
DITA topic shape are untouched**.

The MVP is User Story 1 + 2 together (an analysis sheet authored as `.doc` or
`.docx` ends up embedded inline as an image). User Story 3 (failures visible,
never fatal) falls out of the warn-and-continue posture the script and the
extractor already share with the rest of the pipeline.

**Edited/added files**: new `snapshot_analysis_docs.py`; modified
`extract_to_csv.py` (analysis-row `.doc`/`.docx` → sibling `.png` redirect),
`mock_pptx.py` (emit a `.doc` analysis variant + its rendered sibling so the
existing pipeline tests exercise the new path), `run_pipeline.bat` (insert the
snapshot stage before extract), `README.md` (renderer prerequisites). New tests
`tests/test_snapshot_analysis_docs.py` and extensions to
`tests/test_extract_to_csv.py`, plus updates to two existing tests the changes
break: `tests/test_run_pipeline_bat.py` (new stage order) and
`tests/test_mock_pptx.py` (3-way `{doc,docx,png}` analysis mix). `generate_dita.py`,
`publish_html.py`, `introspect_pptx.py`, `deduplicate_csv.py`, and
`rehydrate_dita.py` are **not** modified.

## Technical Context

**Language/Version**: Python 3.9+ (`from __future__ import annotations`
throughout, string-evaluated modern type hints), per the air-gapped WinPython
3.9.4.0 floor carried from feature 001. Watch the 3.9 gotchas already documented
(`Path.write_text` has no `newline` kwarg).

**Primary Dependencies**: `python-pptx` (extractor only). The new script's
**runtime-critical** path is **stdlib only** (`argparse`, `logging`,
`subprocess`, `pathlib`, `sys`, plus `zipfile`+`xml.etree` for the reverse
`.docx` wrap, reusing `mock_pptx.emit_docx`'s approach). Two **prep-only** tools
sit behind graceful fallbacks: (1) the Word→PNG renderer — an *external tool*
(LibreOffice headless `soffice`) invoked via `subprocess`, like DITA-OT (feature
001 FR-021); (2) **Pillow**, a *defensively-imported* library for margin-trim +
DPI normalisation (FR-017) — `try: import PIL` and fall back to the untrimmed
render when absent. **Neither is added to the pipeline runtime path
(`extract`/`generate`/`publish`) nor required by the test suite** (FR-012):
tests stub the renderer at `--renderer-cmd` and run the crop path only when
Pillow happens to be present (asserting the fallback otherwise), so the canonical
suite stays stdlib-only and LibreOffice/Pillow-free.

**Storage**: Filesystem only. The step writes, beside each analysis document in
its chapter folder (no new directory): a same-stem `.png` (rendered, trimmed) for
every `*analysis*.doc/.docx`, and a same-stem `.docx` for any analysis sheet that
exists only as a `.png` (the reverse wrap, FR-018). The signed-off CSV is
**unchanged in shape** — no new column. The analysis row's existing `png_path`
simply points at the rendered `.png` instead of the `.doc`/`.docx` (and
`target_ext`/`file_size` follow). The DITA tree is unchanged.

**Testing**: `python -m unittest discover tests/` (stdlib `unittest`). New module
`tests/test_snapshot_analysis_docs.py` constructs temp gram folders and stubs
the renderer via `--renderer-cmd` pointing at a tiny script that writes the
project's existing PNG byte template — so the suite stays stdlib-only and
LibreOffice-free. `tests/test_extract_to_csv.py` gains cases for the `.doc`/
`.docx` → sibling `.png` redirect (PNG present → inline path; PNG absent →
recorded warning + dangling image href). The developer-time Jest layer is
untouched.

**Target Platform**: Windows analyst workstations (air-gapped after handover) for
the runtime; Linux/macOS for development except `run_pipeline.bat`. The renderer
runs on the maintainer's prep machine and/or the target PC, once.

**Project Type**: CLI/script tool. One new top-level script following the
existing `verb_noun.py` convention; one modified pipeline stage; test
extensions in paired modules.

**Performance Goals**: The snapshotter shells out to the renderer once per Word
analysis sheet that lacks a PNG (a one-time cost over ~15 decks / ~1,000 grams,
and zero on re-runs because it is idempotent). It adds no work to the
re-runnable generate/publish stages. Extraction gains one `Path.exists()` check
per analysis row.

**Constraints**: Determinism (Principle V) is preserved by treating the rendered
PNG as a **committed source asset**: the renderer's non-reproducible PNG bytes
are produced once and then copied byte-for-byte by `generate_dita.py`'s existing
`copy2` path, so two consecutive generate/publish runs over an unchanged tree
stay byte-identical. The snapshotter is idempotent (skip when the sibling PNG
exists) so re-running it churns nothing. Missing-asset-dangles (the project
invariant) is honoured: a render failure leaves the intended `.png` href in the
topic, resolved later by dropping the PNG in and re-running — no XML churn.

**Scale/Scope**: The feature 001 corpus (~15 decks, ~1,000 grams). Roughly half
the analysis sheets are Word documents (the rest already PNG); of those, the
older decks are legacy binary `.doc`, which is the format that previously had no
inline path at all.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v1.0.0:

- **I. Air-Gapped, Self-Sufficient Operation** — PASS (with a deliberate,
  contained prep-time exception). The pipeline's **runtime** path keeps exactly
  one third-party dependency (`python-pptx`); the new script's runtime-critical
  code is stdlib-only (incl. the reverse `.docx` wrap via `zipfile`+`xml.etree`).
  Two prep-only tools sit behind graceful fallbacks and are never on the runtime
  path or in tests: the external LibreOffice renderer (like DITA-OT), and
  **Pillow** for margin-trim/DPI (FR-017), defensively imported with a full-page
  fallback when absent. This is the maintainer's explicit, justified call to
  allow a prep-time wheel; the constitution's "one dependency" rule binds the
  *runtime* and the rule that *tests* stay stdlib-only — both upheld. The crop
  test runs under `skipUnless(PIL present)` and the fallback is asserted
  unconditionally, so the canonical suite needs neither tool. Python 3.9 floor
  respected; `snapshot.log` honours dual-logging.
- **II. Single-Purpose Scripts, Minimal Surface** — PASS. One new tiny script
  for the one new responsibility (render Word → PNG); the only other change is
  the smallest possible tweak to an existing stage (a sibling-redirect in the
  analysis-row builder). No new directory, no new CSV column, no generator or
  DITA-shape change, no framework. Reuses the existing `copy_asset`/inline-image
  path wholesale.
- **III. Test-First Discipline** — PASS. New behaviour gets paired tests
  (`test_snapshot_analysis_docs.py`, extended `test_extract_to_csv.py`)
  written before/with the source; the canonical `unittest` suite stays green and
  the quickstart is the executable acceptance check.
- **IV. Human-in-the-Loop Authority** — PASS. The script never guesses: a render
  failure, a missing renderer, or a missing sheet is a **WARNING that defers**
  (the run continues, the affected gram is surfaced in `snapshot.log`, the end-
  of-run summary, and the analysis row's `warnings` column), never a fabricated
  value and never a fatal abort. The CSV review boundary is preserved.
- **V. Deterministic, Idempotent Output** — PASS (with the renderer caveat
  handled by design). The renderer's PNG bytes are not byte-reproducible across
  versions, so they (and the trimmed result) are produced **once** and committed
  as source; downstream copy is the existing deterministic `copy2`. The reverse
  `.docx` wrap reuses `emit_docx`'s fixed-timestamp `zipfile` writer, so it is
  byte-stable. The snapshotter is a no-op on an already-rendered/already-wrapped
  tree. See research R2, R9.
- **VI. Honest Limitations** — PASS. The single-landscape-page assumption and the
  first-page-only render behaviour are documented as a known limitation in the
  README and research R3 rather than hidden; the renderer-not-bundled fact is
  stated openly.

**Result**: PASS — no gate violations. Re-evaluated after Phase 1 (contracts,
data-model, quickstart written): still PASS. The total Phase 1 surface is one new
script (stdlib runtime path; two defensively-isolated prep tools), one small
extractor redirect, a mock-corpus addition, a batch wiring line, a README
section, and paired tests — no *runtime* dependency, no CSV/DITA output-shape
change. The single deliberate judgement call (a prep-time Pillow wheel for
FR-017) is contained behind a graceful fallback and excluded from runtime and
tests, per the maintainer's decision.

## Project Structure

### Documentation (this feature)

```text
specs/007-analysis-sheet-images/
├── plan.md                         # This file (/speckit-plan output)
├── spec.md                         # Feature specification (/speckit-specify output)
├── research.md                     # Phase 0 — renderer choice, determinism, page-scope, naming
├── data-model.md                   # Phase 1 — AnalysisSheet states, the doc→png redirect, summary record
├── quickstart.md                   # Phase 1 — end-to-end walkthrough (verifies SC-001…SC-006)
├── contracts/
│   └── snapshot-cli.md            # snapshot_analysis_docs.py CLI + renderer contract + exit codes
├── checklists/
│   └── requirements.md             # Spec quality checklist (complete)
└── tasks.md                        # Phase 2 output (created by /speckit-tasks — NOT here)
```

### Source Code (repository root)

```text
snapshot_analysis_docs.py        # NEW (stdlib only) — prep-time, render-once snapshotter.
                                    #   iter_analysis_sheets(content_root): yield every file matching
                                    #     *analysis* (case-insensitive) with a .doc/.docx extension, anywhere
                                    #     under the tree (analysis docs share the chapter folder with PPT
                                    #     source data + other Word docs, so match by name, NOT "every Word
                                    #     doc"); deterministic sorted order. (research R7)
                                    #   needs_render(doc): True iff no same-stem .png sibling exists.
                                    #   render_doc_to_png(doc, png_out, renderer_cmd): subprocess to
                                    #     `soffice --headless --convert-to png --outdir <tmp> <doc>` (or the
                                    #     configured equivalent), then move the result to the same-stem
                                    #     sibling. Returns True on success; logs WARNING + returns False on
                                    #     renderer-unavailable or non-zero exit. NEVER raises.
                                    #   page_count(doc, renderer_cmd): companion `--convert-to pdf` + stdlib
                                    #     PDF /Count read; >1 → WARN (page-1 image still produced), never
                                    #     silently truncate. (research R3)
                                    #   tidy_image(png): defensively `import PIL`; if present, trim page
                                    #     margins (bounding-box of non-white) + normalise DPI in place; if
                                    #     absent, leave the full-page render and log INFO once. NEVER raises.
                                    #     (FR-017, research R8)
                                    #   wrap_png_in_docx(png, docx_out): stdlib zipfile+xml.etree (reuse
                                    #     mock_pptx.emit_docx pattern, fixed timestamp) embedding the png
                                    #     full-page; only for a sheet that has a .png but no .docx. Returns
                                    #     False on filesystem error; NEVER raises. (FR-018, research R9)
                                    #   main(): scan, classify, render-or-skip, multi-page check, tidy,
                                    #     reverse-wrap, accumulate per-doc INFO/WARNING, write snapshot.log +
                                    #     an end-of-run summary (sheets_seen, rendered, skipped_has_png,
                                    #     render_failed, multipage_warned, docx_wrapped, tidy_skipped).
                                    #     --dry-run logs intent without touching disk. Exit 0 incl.
                                    #     render-failure-with-warnings; 1 only on unhandled error.
                                    #   (FR-001, FR-002, FR-003, FR-006, FR-007, FR-008, FR-011, FR-013,
                                    #    FR-014, FR-015, FR-016, FR-017, FR-018)

extract_to_csv.py                   # MODIFIED — analysis-row builder (~L851-877): after resolving the
                                    #   analysis hyperlink, if its suffix is .doc/.docx, redirect png_path
                                    #   to the same-stem .png sibling (so target_ext/.file_size follow) and,
                                    #   when that .png does not exist on disk, append a
                                    #   "analysis image not rendered" warning. .png/.jpg hyperlinks are
                                    #   unchanged. CSV column set is UNCHANGED. (FR-004, FR-009, FR-010)

mock_pptx.py                        # MODIFIED — extend the analysis-sheet mix from {docx,png} to
                                    #   {doc,docx,png}: for the new "doc" kind, write `analysis table.doc`
                                    #   (placeholder bytes — the mock is not a renderer) AND its rendered
                                    #   sibling `analysis table.png` (the existing PNG byte template), so
                                    #   the full-pipeline tests exercise the doc→inline path deterministically
                                    #   without LibreOffice. (test corpus for US1/US2)

run_pipeline.bat                    # MODIFIED — insert a new first stage before extraction:
                                    #     python snapshot_analysis_docs.py --content-root %1
                                    #   with `if errorlevel 1 goto error`, so the rendered PNGs exist when
                                    #   extract resolves analysis-row png_path. New order: snapshot →
                                    #   extract → pause → generate. (FR-006)

README.md                           # MODIFIED — add a "Renderer prerequisites" section: LibreOffice
                                    #   headless acquisition/install/air-gap transfer + --renderer-cmd
                                    #   override; the OPTIONAL Pillow prep-time wheel for margin-trim/DPI
                                    #   (FR-017) with its graceful-fallback note; both not-bundled /
                                    #   not-runtime-dependencies; and the single-landscape-page /
                                    #   first-page-only-with-warning behaviour. (FR-013, FR-017, Principle VI)

tests/
├── test_snapshot_analysis_docs.py   # NEW (stdlib) — *analysis*.doc → png produced (renderer stubbed
│                                        #   via --renderer-cmd writing the PNG template); *analysis*.docx →
│                                        #   png produced; png-already-present → no re-render, INFO, mtime
│                                        #   preserved (idempotency); renderer-exits-1 → WARNING + run
│                                        #   exits 0 + summary records the failure; --dry-run touches
│                                        #   nothing; MULTI-PAGE source → page-1 png + WARNING (not silent);
│                                        #   NON-analysis Word doc in the same folder (e.g. source_data.doc)
│                                        #   is NOT rendered (the selection-rule guard, research R7);
│                                        #   png-only sheet → minimal valid .docx wrapper produced + is
│                                        #   zip-openable/parseable + idempotent (FR-018); tidy_image
│                                        #   fallback path asserted when PIL is absent, crop asserted only
│                                        #   when PIL is importable (skipUnless) (FR-017).
├── test_extract_to_csv.py               # EXTENDED — .doc/.docx analysis hyperlink with sibling .png →
│                                        #   row png_path is the .png, embedded-inline downstream; sibling
│                                        #   .png absent → png_path still the .png path + "not rendered"
│                                        #   warning (dangling image, not an xref); CSV round-trip + column
│                                        #   count unchanged.
├── test_run_pipeline_bat.py             # UPDATED — assert the new stage order snapshot → extract →
│                                        #   pause → generate (the inserted snapshot stage breaks the
│                                        #   existing order assertion).
├── test_mock_pptx.py                    # UPDATED — the analysis-sheet-mix assertion becomes 3-way
│                                        #   {doc, docx, png} (adding the doc kind breaks the old
│                                        #   docx/(docx+png) ratio check).
└── (existing test_generate_dita.py)     # UNCHANGED — already asserts .png analysis → inline <image>;
                                         #   this feature only changes which path lands in png_path.

specs/001-pptx-dita-migration/contracts/csv-schema.md
                                    # MODIFIED — clarify (no column change) that for analysis rows whose
                                    #   source sheet is .doc/.docx, png_path carries the rendered sibling
                                    #   .png produced by snapshot_analysis_docs.py (feature 007), and
                                    #   that the historical FR-023 `analysis_docx_path` column was never
                                    #   implemented and is not introduced here.
specs/001-pptx-dita-migration/contracts/cli-contracts.md
                                    # MODIFIED — add the snapshot_analysis_docs.py CLI stanza (mirrors
                                    #   contracts/snapshot-cli.md in this feature).
```

`generate_dita.py`, `publish_html.py`, `introspect_pptx.py`, `deduplicate_csv.py`,
and `rehydrate_dita.py` are unchanged.

**Structure Decision**: Same flat repository root as features 001–006 — one new
top-level `verb_noun.py` script (`snapshot_analysis_docs.py`) for the new
responsibility, plus the minimum tweak to the existing extractor. The rendered
PNG (and the reverse `.docx` wrapper) live **beside the analysis document in its
chapter folder** (no new output directory); the extractor points the analysis
row at the `.png`, and the unchanged generator embeds it inline. This deliberately diverges from feature 001's
sketched FR-023 (which assumed a canonical `Analysis.png` and a new
`analysis_docx_path` column): the same-stem sibling needs neither a canonical
name nor a CSV-shape change, which is the smaller surface (Principle II).

## Complexity Tracking

> No constitution violations to justify. The one external moving part — the
> LibreOffice renderer — is mandated by the spec's core finding (the analysis
> "tables" are eye-aligned text blocks, so they must be rendered as an image,
> not parsed) and is contained to a prep-time `subprocess` call behind a
> configurable, test-stubbable `--renderer-cmd`, exactly as DITA-OT is contained.
> Everything inside the air-gapped runtime path stays stdlib + `python-pptx`.

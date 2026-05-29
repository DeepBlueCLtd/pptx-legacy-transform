# Implementation Plan: Analysis-Sheet Images (render Word analysis sheets to PNG)

**Branch**: `claude/brave-gauss-CIG8Z` (developed on the existing working branch; no separate feature branch) | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-analysis-sheet-images/spec.md`

## Summary

Make every gram's analysis table show **inline** in the topic — the fast,
intuitive experience the PNG-backed grams already give — by rendering the
analysis sheet's single landscape page to a PNG ahead of time, instead of
leaving a click-to-open link that launches MS Word mid-lesson.

The mechanism is a new **prep-time, single-purpose script**
`normalise_analysis_sheets.py` that walks the content tree and, for every
analysis sheet authored as a Word document (legacy binary `.doc` *or* `.docx`),
renders a sibling PNG (`analysis table.doc` → `analysis table.png`) via an
external, configurable renderer (LibreOffice headless by default). It is
**render-once and idempotent**: a sheet that already has its PNG is skipped, so
the produced image becomes a committed source asset and the renderer never runs
inside a re-runnable generate/publish loop.

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

**Edited/added files**: new `normalise_analysis_sheets.py`; modified
`extract_to_csv.py` (analysis-row `.doc`/`.docx` → sibling `.png` redirect),
`mock_pptx.py` (emit a `.doc` analysis variant + its rendered sibling so the
existing pipeline tests exercise the new path), `run_pipeline.bat` (insert the
normalise stage before extract), `README.md` (renderer prerequisites). New tests
`tests/test_normalise_analysis_sheets.py` and extensions to
`tests/test_extract_to_csv.py`. `generate_dita.py`, `publish_html.py`,
`introspect_pptx.py`, `deduplicate_csv.py`, and `rehydrate_dita.py` are **not**
modified.

## Technical Context

**Language/Version**: Python 3.9+ (`from __future__ import annotations`
throughout, string-evaluated modern type hints), per the air-gapped WinPython
3.9.4.0 floor carried from feature 001. Watch the 3.9 gotchas already documented
(`Path.write_text` has no `newline` kwarg).

**Primary Dependencies**: `python-pptx` (extractor only — the new script imports
**stdlib only**: `argparse`, `logging`, `subprocess`, `pathlib`, `sys`). **No
new runtime Python dependency.** The Word→PNG renderer is an *external tool*
(LibreOffice headless `soffice`), invoked via `subprocess` — not a Python
package, not bundled, installed by the maintainer, exactly as DITA-OT is treated
(feature 001 FR-021). Tests stub it at the `--renderer-cmd` boundary and never
require LibreOffice.

**Storage**: Filesystem only. The renderer writes one sibling `.png` per Word
analysis sheet into the gram folder it already lives in (no new directory). The
signed-off CSV is **unchanged in shape** — no new column. The analysis row's
existing `png_path` simply points at the rendered `.png` instead of the `.doc`/
`.docx` (and `target_ext`/`file_size` follow). The DITA tree is unchanged.

**Testing**: `python -m unittest discover tests/` (stdlib `unittest`). New module
`tests/test_normalise_analysis_sheets.py` constructs temp gram folders and stubs
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

**Performance Goals**: The normaliser shells out to the renderer once per Word
analysis sheet that lacks a PNG (a one-time cost over ~15 decks / ~1,000 grams,
and zero on re-runs because it is idempotent). It adds no work to the
re-runnable generate/publish stages. Extraction gains one `Path.exists()` check
per analysis row.

**Constraints**: Determinism (Principle V) is preserved by treating the rendered
PNG as a **committed source asset**: the renderer's non-reproducible PNG bytes
are produced once and then copied byte-for-byte by `generate_dita.py`'s existing
`copy2` path, so two consecutive generate/publish runs over an unchanged tree
stay byte-identical. The normaliser is idempotent (skip when the sibling PNG
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

- **I. Air-Gapped, Self-Sufficient Operation** — PASS. **No new runtime Python
  dependency**: the new script is stdlib-only and the Word→PNG renderer is an
  external, installed-by-the-user, documented-in-README tool (like DITA-OT),
  never invoked at pipeline runtime by the re-runnable stages. Tests stay
  stdlib-only by stubbing the renderer at `--renderer-cmd`. Python 3.9 floor
  respected. The script writes a `normalise.log` DEBUG file alongside console
  output, per the dual-logging rule.
- **II. Single-Purpose Scripts, Minimal Surface** — PASS. One new tiny script
  for the one new responsibility (render Word → PNG); the only other change is
  the smallest possible tweak to an existing stage (a sibling-redirect in the
  analysis-row builder). No new directory, no new CSV column, no generator or
  DITA-shape change, no framework. Reuses the existing `copy_asset`/inline-image
  path wholesale.
- **III. Test-First Discipline** — PASS. New behaviour gets paired tests
  (`test_normalise_analysis_sheets.py`, extended `test_extract_to_csv.py`)
  written before/with the source; the canonical `unittest` suite stays green and
  the quickstart is the executable acceptance check.
- **IV. Human-in-the-Loop Authority** — PASS. The script never guesses: a render
  failure, a missing renderer, or a missing sheet is a **WARNING that defers**
  (the run continues, the affected gram is surfaced in `normalise.log`, the end-
  of-run summary, and the analysis row's `warnings` column), never a fabricated
  value and never a fatal abort. The CSV review boundary is preserved.
- **V. Deterministic, Idempotent Output** — PASS (with the renderer caveat
  handled by design). The renderer's PNG bytes are not byte-reproducible across
  versions, so they are produced **once** and committed as source; downstream
  copy is the existing deterministic `copy2`. The normaliser is a no-op on an
  already-rendered tree. See research R2.
- **VI. Honest Limitations** — PASS. The single-landscape-page assumption and the
  first-page-only render behaviour are documented as a known limitation in the
  README and research R3 rather than hidden; the renderer-not-bundled fact is
  stated openly.

**Result**: PASS — no gate violations. Re-evaluated after Phase 1 (contracts,
data-model, quickstart written): still PASS. The total Phase 1 surface is one
new stdlib script, one small extractor redirect, a mock-corpus addition, a batch
wiring line, a README section, and paired tests — no dependency, no output-shape
change.

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
│   └── normalise-cli.md            # normalise_analysis_sheets.py CLI + renderer contract + exit codes
├── checklists/
│   └── requirements.md             # Spec quality checklist (complete)
└── tasks.md                        # Phase 2 output (created by /speckit-tasks — NOT here)
```

### Source Code (repository root)

```text
normalise_analysis_sheets.py        # NEW (stdlib only) — prep-time, render-once normaliser.
                                    #   iter_analysis_sheets(content_root): yield every .doc/.docx whose
                                    #     role/name marks it an analysis sheet (case-insensitive, same
                                    #     whitelist the extractor uses), deterministic sorted order.
                                    #   needs_render(doc): True iff no same-stem .png sibling exists.
                                    #   render_doc_to_png(doc, png_out, renderer_cmd): subprocess to
                                    #     `soffice --headless --convert-to png --outdir <tmp> <doc>` (or the
                                    #     configured equivalent), then move the result to the same-stem
                                    #     sibling. Returns True on success; logs WARNING + returns False on
                                    #     renderer-unavailable or non-zero exit. NEVER raises.
                                    #   main(): walk, classify, render-or-skip, accumulate per-sheet
                                    #     INFO/WARNING, write normalise.log + an end-of-run summary
                                    #     (sheets_seen, rendered, already_png_skipped, render_failures).
                                    #     --dry-run logs intent without touching disk. Exit 0 incl.
                                    #     render-failure-with-warnings; 1 only on unhandled error.
                                    #   (FR-001, FR-002, FR-003, FR-006, FR-007, FR-008, FR-011, FR-013, FR-014)

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
                                    #     python normalise_analysis_sheets.py --content-root %1
                                    #   with `if errorlevel 1 goto error`, so the rendered PNGs exist when
                                    #   extract resolves analysis-row png_path. New order: normalise →
                                    #   extract → pause → generate. (FR-006)

README.md                           # MODIFIED — add a "Renderer prerequisites (LibreOffice headless)"
                                    #   section: acquisition, install on dev + air-gapped PC, air-gap
                                    #   transfer, the --renderer-cmd override, the not-bundled / not-a-Python-
                                    #   dependency note, and the single-landscape-page / first-page-only
                                    #   limitation. (FR-013, Principle VI)

tests/
├── test_normalise_analysis_sheets.py   # NEW (stdlib) — doc-only folder → png produced (renderer stubbed
│                                        #   via --renderer-cmd writing the PNG template); docx-only →
│                                        #   png produced; png-already-present → no re-render, INFO, mtime
│                                        #   preserved (idempotency); renderer-exits-1 → WARNING + run
│                                        #   exits 0 + summary records the failure; missing sheet → WARNING;
│                                        #   --dry-run touches nothing.
├── test_extract_to_csv.py               # EXTENDED — .doc/.docx analysis hyperlink with sibling .png →
│                                        #   row png_path is the .png, embedded-inline downstream; sibling
│                                        #   .png absent → png_path still the .png path + "not rendered"
│                                        #   warning (dangling image, not an xref); CSV round-trip + column
│                                        #   count unchanged.
└── (existing test_generate_dita.py)     # UNCHANGED — already asserts .png analysis → inline <image>;
                                         #   this feature only changes which path lands in png_path.

specs/001-pptx-dita-migration/contracts/csv-schema.md
                                    # MODIFIED — clarify (no column change) that for analysis rows whose
                                    #   source sheet is .doc/.docx, png_path carries the rendered sibling
                                    #   .png produced by normalise_analysis_sheets.py (feature 007), and
                                    #   that the historical FR-023 `analysis_docx_path` column was never
                                    #   implemented and is not introduced here.
specs/001-pptx-dita-migration/contracts/cli-contracts.md
                                    # MODIFIED — add the normalise_analysis_sheets.py CLI stanza (mirrors
                                    #   contracts/normalise-cli.md in this feature).
```

`generate_dita.py`, `publish_html.py`, `introspect_pptx.py`, `deduplicate_csv.py`,
and `rehydrate_dita.py` are unchanged.

**Structure Decision**: Same flat repository root as features 001–006 — one new
top-level `verb_noun.py` script (`normalise_analysis_sheets.py`) for the new
responsibility, plus the minimum tweak to the existing extractor. The rendered
PNG lives **in the gram folder beside its source Word document** (no new output
directory); the extractor points the analysis row at it, and the unchanged
generator embeds it inline. This deliberately diverges from feature 001's
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

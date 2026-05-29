# Quickstart: Analysis-Sheet Images

End-to-end walkthrough that doubles as the executable acceptance check for the
success criteria. Uses the synthetic corpus (no real decks needed). Run from the
repo root.

## Prerequisites

- Python 3.9+ and `python-pptx` (the project's one runtime dependency).
- For a *real* render: LibreOffice headless (`soffice`) on PATH. For the
  synthetic walkthrough and the test suite, the renderer is **not** required —
  the mock corpus ships pre-rendered siblings and the tests stub the renderer.

## 1. Generate a synthetic corpus that includes a `.doc` analysis sheet

```bash
python mock_pptx.py --out mock_instructor.pptx
```

The mock generator now emits a `{doc, docx, png}` mix of analysis sheets. For a
`doc`-kind gram it writes both `analysis table.doc` and its rendered sibling
`analysis table.png` (so the walkthrough is deterministic and LibreOffice-free).

## 2. Normalise: render any un-rendered Word analysis sheet to PNG

```bash
python normalise_analysis_sheets.py --content-root path/to/content
# add --renderer-cmd /path/to/soffice on a real corpus; omit for the mock
```

**Verify (SC-001, SC-005)**: the end-of-run summary reports `sheets_seen`,
`rendered`, `skipped_has_png`, `render_failed`, `missing`. Every `.doc`/`.docx`
sheet now has a same-stem `.png` sibling, except any reported under
`render_failed`. `normalise.log` records one line per sheet.

**Verify idempotency (SC-004)**: run the same command again — every sheet is
`skipped_has_png`, nothing is written, no PNG mtime changes.

## 3. Extract → review CSV

```bash
python extract_to_csv.py --input-root path/to/content --out extracted.csv
```

**Verify (SC-001)**: each analysis row's `png_path` ends in `.png` (the rendered
sibling for Word-sourced sheets). **Verify (US3 / FR-009)**: any sheet that
failed to render shows its analysis row's `warnings` column containing
`analysis image not rendered`, so the author sees it in Excel without reading
logs. The CSV column count is unchanged from before this feature.

## 4. Generate DITA

```bash
python generate_dita.py --csv extracted.csv --out dita/ --image-root path/to/content
```

**Verify (SC-002, SC-003 — the headline)**: open a Word-sourced gram's topic
(`dita/.../gram-NN/gram_NN.dita`). Its **Analysis Sheet** section contains an
inline `<image>` referencing the local `.png` — **not** an `<xref>` link to a
`.doc`/`.docx` that would launch MS Word. The analysis table now displays
inline, instantly.

**Verify dangling-not-fatal (FR-010)**: for a gram whose render failed, the
section still emits the intended local `<image href="…analysis….png">`; dropping
the PNG into the gram folder and re-running `generate_dita.py` resolves it with
no other change to the topic XML.

## 5. (Optional) HTML preview

```bash
python publish_html.py --dita-ot /path/to/dita-ot-4.2.4
```

**Verify (SC-003)**: in `html/instructor/`, the gram page shows the analysis
table as an inline image with no click-to-open step. **Verify (SC-004)**: a
second `publish_html.py` run over the unchanged tree yields byte-identical HTML.

## 6. Run the canonical test suite

```bash
python -m unittest discover tests/
```

**Verify**: `tests/test_normalise_analysis_sheets.py` (render/skip/fail/missing,
idempotency, dry-run — renderer stubbed) and the extended
`tests/test_extract_to_csv.py` (doc/docx → sibling-png redirect, warning on
absent PNG, unchanged column count) are green, with the rest of the suite.

## Success-criteria coverage map

| Criterion | Step that verifies it |
|---|---|
| SC-001 (every doc/docx sheet has a PNG) | 2, 3 |
| SC-002 (inline rather than Word-launch) | 4, 5 |
| SC-003 (instructor sees table instantly) | 4, 5 |
| SC-004 (byte-identical re-runs) | 2 (idempotent), 5 |
| SC-005 (failures complete + visible) | 2 (summary), 3 (CSV warning) |
| SC-006 (identify failures in <1 min) | 2 (summary line) |

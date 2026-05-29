# Phase 1 Data Model: Analysis-Sheet Images

This feature introduces **no new persisted schema** — no new CSV column, no new
DITA element, no new output directory. It adds one transient in-memory record
(the normaliser's per-sheet result) and changes *which value* an existing CSV
field carries for Word-sourced analysis rows. The entities below describe those
states and transitions.

## 1. `AnalysisSheetSource` *(on-disk, per gram folder — conceptual)*

The analysis artefact a gram folder carries on disk. One per gram folder.

| Field | Type | Source | Notes |
|---|---|---|---|
| `gram_folder` | `pathlib.Path` | filesystem | the folder the sheet lives in |
| `source_path` | `pathlib.Path` | filesystem | the authored sheet: `*.doc`, `*.docx`, `*.png`, or `*.jpg/.jpeg` |
| `source_kind` | `str` | derived from suffix | `"doc"`, `"docx"`, or `"image"` |
| `rendered_png` | `pathlib.Path \| None` | derived | for `doc`/`docx`: the same-stem `.png` sibling (`source_path.with_suffix(".png")`); `None`/N-A for an image source |

**State** (what exists on disk for a Word-sourced sheet):

```
authored .doc/.docx, no sibling .png      → NEEDS_RENDER
authored .doc/.docx, sibling .png present → RENDERED (committed source asset)
authored .png/.jpg                        → IMAGE (no rendering needed)
```

## 2. `NormaliseResult` *(transient, per analysis sheet — produced by the normaliser)*

Not persisted; drives logging and the end-of-run summary only.

| Field | Type | Values | Notes |
|---|---|---|---|
| `source_path` | `pathlib.Path` | — | the sheet processed |
| `outcome` | `str` | `"rendered"`, `"skipped_has_png"`, `"render_failed"`, `"missing"` | one per sheet visited |
| `warning` | `str \| None` | — | populated for `render_failed`/`missing`; surfaces in `normalise.log` |

**State transitions** (per sheet):

```
NEEDS_RENDER + renderer ok      → outcome=rendered        (writes sibling .png; INFO)
NEEDS_RENDER + renderer fails   → outcome=render_failed   (no .png; WARNING; run continues, exit 0)
NEEDS_RENDER + renderer absent  → outcome=render_failed   (no .png; WARNING; run continues, exit 0)
RENDERED (png already present)  → outcome=skipped_has_png (no re-render; mtime preserved; INFO)
no sheet at all in folder       → outcome=missing         (WARNING; run continues, exit 0)
```

**End-of-run summary** (logged + printed, per FR-014): `sheets_seen`,
`rendered`, `skipped_has_png`, `render_failed`, `missing`.

**Validation / invariants**:
- The normaliser **never raises** on a renderer problem; it records a result and
  moves on (Principle IV).
- `outcome=rendered` is the **only** state that writes to disk. `skipped_has_png`
  must not touch the existing `.png` (idempotency / determinism, R2).
- Re-running over a tree of all-`RENDERED`/`IMAGE` sheets yields all
  `skipped_has_png`/(n-a) and zero disk writes.

## 3. CSV analysis row — `png_path` semantics (existing field, refined value)

**No column added or removed.** `CSV_COLUMNS` in `extract_to_csv.py` is
unchanged. For an **analysis row** (`topic_type == "analysis"`) the `png_path`
field's *value* is refined:

| Authored analysis hyperlink target | `png_path` recorded | `target_ext` | `warnings` addition |
|---|---|---|---|
| `*.png` / `*.jpg` | the image path (as today) | `.png`/`.jpg` | — |
| `*.doc` / `*.docx`, sibling `.png` present | the **sibling `.png`** path | `.png` | — |
| `*.doc` / `*.docx`, sibling `.png` **absent** | the sibling `.png` path (intended href) | `.png` | `"analysis image not rendered"` |

`file_size` follows `png_path` (size of the `.png`, or empty when absent).

**Consequence downstream (unchanged code)**: `generate_dita.py` copies
`png_path` (`copy_asset`) and `_append_analysis_section` embeds it inline because
the suffix is now `.png` (line 646). An absent `.png` dangles as an `<image>`
href — the intended local reference — per the missing-asset invariant (FR-010),
*not* as a Word `<xref>`.

## 4. Relationship to feature 001's FR-023 (historical)

Feature 001 sketched an `AnalysisSheet` entity (`data-model.md §1.7`) and an
`analysis_docx_path` CSV column produced by a bidirectional normaliser. **That
column was never implemented** (it is absent from `CSV_COLUMNS`). This feature
implements the forward direction (Word → PNG) only, via the same-stem sibling
and **without** introducing `analysis_docx_path` (research R4). The 001 contracts
are updated to record this rather than left implying a column that does not
exist (Principle VI).

# Phase 1 Data Model: Analysis-Sheet Images

This feature introduces **no new persisted schema** — no new CSV column, no new
DITA element, no new output directory. It adds one transient in-memory record
(the snapshotter's per-sheet result) and changes *which value* an existing CSV
field carries for Word-sourced analysis rows. The entities below describe those
states and transitions.

## 1. `AnalysisSheetSource` *(on-disk — conceptual)*

An analysis document found on disk. Analysis sheets live in the **chapter
folder alongside other files** (PPT source data, unrelated Word docs), and follow
the corpus naming convention `*analysis*` (e.g. `aaa_analysis.doc`). The
snapshotter selects them by that **name pattern + `.doc`/`.docx` extension** — not
by folder position and not "every Word doc in the folder" (see research R7).

| Field | Type | Source | Notes |
|---|---|---|---|
| `source_path` | `pathlib.Path` | filesystem | a `*analysis*.doc` / `*analysis*.docx` document (a `.png`/`.jpg` analysis export needs no rendering and is handled directly by the extractor) |
| `source_kind` | `str` | derived from suffix | `"doc"` or `"docx"` |
| `rendered_png` | `pathlib.Path \| None` | derived | the same-stem `.png` sibling (`source_path.with_suffix(".png")`) |

**State** (what exists on disk for a Word-sourced sheet):

```
*analysis*.doc/.docx, no sibling .png      → NEEDS_RENDER
*analysis*.doc/.docx, sibling .png present → RENDERED (committed source asset)
analysis .png/.jpg (no Word source)        → IMAGE (no rendering needed)
```

## 2. `SnapshotResult` *(transient, per analysis sheet — produced by the snapshotter)*

Not persisted; drives logging and the end-of-run summary only.

| Field | Type | Values | Notes |
|---|---|---|---|
| `source_path` | `pathlib.Path` | — | the analysis document processed |
| `outcome` | `str` | `"rendered"`, `"skipped_has_png"`, `"render_failed"` | one per document visited |
| `multipage` | `bool` | — | `True` when the source has >1 page (page 1 still rendered; WARNING) |
| `tidied` | `bool` | — | `True` when margin-trim/DPI applied; `False` when the image library was absent and the full-page render was kept (FR-017) |
| `docx_wrapped` | `bool` | — | `True` when a reverse `.docx` wrapper was produced for a png-only sheet (FR-018) |
| `warning` | `str \| None` | — | populated for `render_failed` and `multipage`; surfaces in `snapshot.log` |

**State transitions** (per document):

```
NEEDS_RENDER + renderer ok          → outcome=rendered        (writes sibling .png; INFO)
NEEDS_RENDER + renderer ok + >1page → outcome=rendered        (page-1 .png; multipage=True; WARNING)
NEEDS_RENDER + renderer fails       → outcome=render_failed   (no .png; WARNING; run continues, exit 0)
NEEDS_RENDER + renderer absent      → outcome=render_failed   (no .png; WARNING; run continues, exit 0)
RENDERED (png already present)      → outcome=skipped_has_png (no re-render; mtime preserved; INFO)
```

A document **with no analysis sheet at all** is *not* a snapshotter state — the
snapshotter only visits files that match `*analysis*.{doc,docx}`. Missing-sheet
detection lives in the extractor (`"missing analysis PNG hyperlink"`), avoiding a
duplicated responsibility (research R7, DRY).

**End-of-run summary** (logged + printed, per FR-014): `sheets_seen`,
`rendered`, `skipped_has_png`, `render_failed`, `multipage_warned`,
`docx_wrapped`, `tidy_skipped`.

**Validation / invariants**:
- The snapshotter **never raises** on a renderer problem, an absent image library,
  or a wrap failure; it records a result and moves on (Principle IV).
- Disk writes happen for `rendered` (the `.png`, trimmed in place) and for a
  reverse `.docx` wrap. `skipped_has_png` must not touch the existing `.png`
  (idempotency / determinism, R2); a sheet that already has its `.docx` is not
  re-wrapped (R9).
- A multi-page source is **never silently truncated**: page 1 is rendered *and* a
  WARNING is emitted (research R3).
- Margin-trim/DPI (FR-017) degrades gracefully: absent image library → full-page
  render kept, `tidied=False`, INFO logged, never a failure (research R8).
- The reverse `.docx` wrap reuses the fixed-timestamp `emit_docx` writer, so it
  is byte-stable (research R9).
- Re-running over a tree of all-`RENDERED`/`IMAGE` sheets (each with its `.docx`)
  yields all `skipped_has_png`/(n-a) and zero disk writes.

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
`analysis_docx_path` CSV column produced by a bidirectional snapshotter. **That
column was never implemented** (it is absent from `CSV_COLUMNS`). This feature
implements the forward direction (Word → PNG) only, via the same-stem sibling
and **without** introducing `analysis_docx_path` (research R4). The 001 contracts
are updated to record this rather than left implying a column that does not
exist (Principle VI).

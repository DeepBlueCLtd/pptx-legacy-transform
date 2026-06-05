# Contract: `snapshot_analysis_docs.py` CLI

Prep-time, render-once snapshot stage. Walks a content tree and renders
every Word analysis sheet (`.doc` / `.docx`) to a same-stem `.png` sibling so
the downstream pipeline embeds the analysis table inline. Authoritative schema
for the script's command-line interface, behaviour, and exit codes.

## Invocation

```text
python snapshot_analysis_docs.py --content-root <dir> [--renderer-cmd <cmd>] [--dry-run]
```

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--content-root <dir>` | yes | — | Root of the content tree to walk for analysis sheets. |
| `--renderer-cmd <cmd>` | no | `soffice` | Renderer executable/command used to convert a Word document to PNG/PDF. Allows substituting an equivalent converter or a test stub. |
| `--dry-run` | no | off | Log what *would* be rendered/wrapped/skipped without writing any file. |

## Behaviour

1. **Discover** analysis documents by scanning the content tree for files whose
   **name matches `*analysis*` (case-insensitive)** and whose extension is
   `.doc` or `.docx`. Analysis documents live in the **chapter folder alongside
   other files** (PPT source data, unrelated Word docs), so selection keys on
   the analysis naming convention — it does **not** render every Word document it
   finds. Iteration is deterministic (sorted).
2. **Classify** each: if a same-stem `.png` sibling already exists →
   `skipped_has_png` (no action, existing PNG untouched). Otherwise →
   render.
3. **Render** via `--renderer-cmd`. The default LibreOffice invocation is
   `<cmd> --headless --convert-to png --outdir <tmp> <doc>`; the produced PNG is
   moved to the same-stem sibling beside the source. On success → `rendered`
   (INFO). On non-zero exit or unavailable renderer → `render_failed` (WARNING);
   the run continues.
4. **Multi-page check**: render the **first page** as the image, and detect when
   the source has more than one page (via a companion `--convert-to pdf` and a
   stdlib page-count read — see research R3). When pages `> 1` → still produce
   the page-1 PNG but emit a WARNING and mark the result so the extractor flags
   the row; the sheet is **never silently truncated**.
5. **Tidy** (FR-017): trim page-margin whitespace and normalise DPI on the
   rendered PNG via a **defensively-imported** image library (Pillow). If the
   library is unavailable, leave the full-page render in place and log an INFO
   line — never fail. (research R8)
6. **Reverse wrap** (FR-018): for an analysis sheet that has a `.png` but no
   same-stem `.docx`, emit a minimal full-page `.docx` embedding the image, using
   the stdlib `zipfile`+`xml.etree` approach (no dependency). Skip when the
   `.docx` already exists (idempotent). (research R9)
7. **Summary**: emit an end-of-run summary line (`sheets_seen`, `rendered`,
   `skipped_has_png`, `render_failed`, `multipage_warned`, `docx_wrapped`,
   `tidy_skipped`) to the log and console. (A gram with *no* analysis document is
   detected by the extractor, not here.)

## Logging

- Writes a DEBUG log file `snapshot.log` at the repository root **and** mirrors
  to console (dual-logging, per the project convention / Principle I).
- One INFO line per sheet for `rendered` / `skipped_has_png`; one WARNING line
  per sheet for `render_failed` and for a multi-page sheet (`multipage_warned`).

## Idempotency

Re-running over a tree whose Word sheets already have their `.png` siblings is a
**no-op**: every sheet classifies as `skipped_has_png`, no file is written, and
existing PNG mtimes are preserved. The rendered PNG is a committed source asset;
the renderer never runs inside the re-runnable generate/publish loop.

## Exit codes

| Code | Condition |
|---|---|
| `0` | Success — **including** runs with render failures or missing sheets (these are warnings, surfaced in the summary, not fatal). |
| `1` | Unhandled error (e.g. `--content-root` does not exist, unreadable tree). |
| `2` | Usage error (missing/invalid arguments). |

## Guarantees

- **Never raises** on a renderer problem, a missing image library, or a wrap
  failure (unavailable, crash, non-zero exit) — it records a warning/INFO and
  continues (Principle IV).
- **No new *runtime* Python dependency.** The script's runtime-critical path is
  stdlib + `subprocess`. The external LibreOffice renderer and the optional
  Pillow image library are **prep-only**, both behind graceful fallbacks, neither
  on the pipeline runtime path nor required by the test suite (FR-012).
- **No CSV or DITA shape change** — the script only writes `.png` (and, for the
  reverse wrap, `.docx`) files beside their source documents.

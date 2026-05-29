# Contract: `normalise_analysis_sheets.py` CLI

Prep-time, render-once normalisation stage. Walks a content tree and renders
every Word analysis sheet (`.doc` / `.docx`) to a same-stem `.png` sibling so
the downstream pipeline embeds the analysis table inline. Authoritative schema
for the script's command-line interface, behaviour, and exit codes.

## Invocation

```text
python normalise_analysis_sheets.py --content-root <dir> [--renderer-cmd <cmd>] [--dry-run]
```

| Flag | Required | Default | Meaning |
|---|---|---|---|
| `--content-root <dir>` | yes | — | Root of the content tree to walk for analysis sheets. |
| `--renderer-cmd <cmd>` | no | `soffice` | Renderer executable/command used to convert a Word document to PNG. Allows substituting an equivalent converter or a test stub. |
| `--dry-run` | no | off | Log what *would* be rendered/skipped without writing any file. |

## Behaviour

1. **Discover** every analysis sheet under `--content-root` whose extension is
   `.doc` or `.docx` (case-insensitive), identified by the same analysis-sheet
   role/whitelist the extractor uses. Iteration is deterministic (sorted).
2. **Classify** each: if a same-stem `.png` sibling already exists →
   `skipped_has_png` (no action, existing PNG untouched). Otherwise →
   render.
3. **Render** via `--renderer-cmd`. The default LibreOffice invocation is
   `<cmd> --headless --convert-to png --outdir <tmp> <doc>`; the produced PNG is
   moved to the same-stem sibling beside the source. On success → `rendered`
   (INFO). On non-zero exit or unavailable renderer → `render_failed` (WARNING);
   the run continues.
4. **Missing**: a gram folder with no analysis sheet at all → `missing`
   (WARNING); the run continues.
5. **Summary**: emit an end-of-run summary line (`sheets_seen`, `rendered`,
   `skipped_has_png`, `render_failed`, `missing`) to the log and console.

## Logging

- Writes a DEBUG log file `normalise.log` at the repository root **and** mirrors
  to console (dual-logging, per the project convention / Principle I).
- One INFO line per sheet for `rendered` / `skipped_has_png`; one WARNING line
  per sheet for `render_failed` / `missing`.

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

- **Never raises** on a renderer problem (unavailable, crash, non-zero exit) — it
  records a warning and continues (Principle IV).
- **No new runtime Python dependency**; stdlib + `subprocess` only. The renderer
  is an external, installed-by-the-user tool, not bundled.
- **No CSV or DITA shape change** — the script only writes `.png` files beside
  their source documents.

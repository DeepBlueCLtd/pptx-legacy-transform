# Air-gap handover

Companion doc to `README.md`, written for the target-side analyst.
Assumes the target already has WinPython 3.9.4.0, VS Code, Oxygen XML
Author, and DITA-OT 4.2.4 installed; this bundle adds only the
pipeline scripts and their two Python dependencies.

## What's in this bundle

| Path | Why |
|---|---|
| `extract_to_csv.py`, `generate_dita.py`, `introspect_pptx.py`, `mock_pptx.py`, `publish_html.py` | The five pipeline scripts. |
| `run_pipeline.bat` | Windows orchestrator (extract → review → generate). |
| `vendor/gramframe/gramframe.bundle.js` | Spectrogram-viewer plugin injected by `publish_html.py`. |
| `vendor/themes/operator-console-v2/theme.css` | Dark theme injected by `publish_html.py`. |
| `tests/` (with `tests/fixtures/`) | Standard-library `unittest` suite + 296 KB of self-contained fixtures. |
| `wheels/` | Offline-installable wheels for `python-pptx` and `lxml` (cp39 / win_amd64). |
| `README.md` | Full reference: CSV schema, troubleshooting, publish layout. |
| `HANDOVER.md` | This file. |

Not shipped (deliberately):

- The mock corpus under `source/` — the real corpus is already on the
  target.
- Any previously generated `dita/`, `html/`, `extracted.csv` — those
  are pipeline outputs and will be created/refreshed by a run.
- `presentation/`, `specs/`, jest/npm files — dev-side only.

## One-time setup

1. Copy the bundle to a stable working directory on the target (e.g.
   `C:\projects\pptx-legacy-transform\`).

2. Install the two Python deps from the offline wheelhouse. From the
   bundle root, in a shell where `python` is WinPython 3.9.4.0:

   ```cmd
   python -m pip install --no-index --find-links=wheels python-pptx lxml
   ```

3. Confirm the install:

   ```cmd
   python -c "import pptx, lxml; print(pptx.__version__, lxml.__version__)"
   ```

## Smoke test

Before pointing the pipeline at the real corpus, verify the bundle
itself is healthy:

```cmd
python -m unittest discover tests
```

Expected: all tests pass in under a minute.

## Daily workflow

Two manual steps (the .bat handles steps 1+2, you handle step 3).

1. **Extract + generate** against the real corpus:

   ```cmd
   run_pipeline.bat <path-to-corpus-root>
   ```

   The script runs `extract_to_csv.py`, pauses for CSV review, then
   runs `generate_dita.py`. Outputs: `extracted.csv` at the bundle
   root, DITA tree at `dita/`.

2. **Review `extracted.csv`** in Excel during the pause. Edit only the
   author-editable columns (`vessel_name`, `warnings`, asset paths).
   See README.md §"CSV column reference" for the full schema and the
   Excel "Save As" gotchas (BOM, line endings, leading zeros).

3. **Publish** to HTML. Two options:

   - **From Oxygen** (preferred): open `dita/main.ditamap` (or a
     `progress-test-*.ditamap`) and use the publish dialog. For the
     student edition, select `dita/trainee.ditaval` as the DITAVAL
     filter. The Oxygen template must link `theme.css` and
     `gramframe.bundle.js` from the `vendor/` paths above — otherwise
     the published pages will render unstyled.

   - **From the command line** (faster for full-corpus republish):

     ```cmd
     python publish_html.py --dita-ot C:\path\to\dita-ot-4.2.4
     ```

     This produces both editions under `html/instructor/` and
     `html/student/` plus a shared landing page at `html/index.html`.
     The script handles staging, DOCTYPE injection, theme/plugin
     linking, and idempotent re-runs.

## What's safe to delete

These are all regenerated on the next pipeline run:

- `extracted.csv`
- `dita/` (entire tree, including `dita/trainee.ditaval`)
- `html/`
- `.dita-build/` (publisher staging; auto-cleaned but harmless to nuke)
- `*.log` at the root (`extract.log`, `generate.log`, `introspect.log`)

The bundled scripts, `tests/`, `vendor/`, and `wheels/` are never
written to by the pipeline.

## If something breaks

1. Read the script's log at the bundle root (`extract.log`,
   `generate.log`).
2. Re-run a single failing test for tighter feedback, e.g.
   `python -m unittest tests.test_generate_dita.GenerateDitaTests.test_glc_topic_structure`.
3. README.md §"Troubleshooting" enumerates the common failure modes
   and their fixes.

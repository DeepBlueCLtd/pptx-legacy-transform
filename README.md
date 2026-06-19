# pptx-legacy-transform

A defensive five-stage pipeline that migrates legacy AAAC PowerPoint
instructor presentations into DITA XML publications matching the
existing pub-9/pub-10 structure. The pipeline is built to remain
debuggable on an air-gapped network without internet or AI
assistance: tiny scripts, a minimal and individually justified set of
dependencies, dual-output logging, and a `unittest`-based test suite.

## Project context

Roughly 15 instructor PowerPoint decks containing ~1,000 acoustic
training "grams" must become DITA topics that the modern publishing
toolchain (Oxygen) renders in both an instructor profile and a
trainee profile. Each gram has a title with vessel name, a hyperlinked
analysis sheet, and one or more `Lofar`-labelled hyperlinks that
**always** point to a `.glc` configuration file. The `.glc` in turn
references a sibling asset: usually a `.png` / `.jpg` / `.gif` (~82%,
pre-rendered spectrogram), occasionally a `.wav` (~18%, raw audio
rendered live by the on-PC GLC viewer). The generator dispatches on
the inner asset extension: image assets are embedded inline, audio
assets are surfaced as a link to the `.glc` (with both `.glc` and
`.wav` copied next to the topic so the viewer can resolve the audio).
The pipeline extracts everything into an intermediate CSV, lets the
technical author triage warnings in Excel, then emits the deterministic
DITA tree.

See [`specs/001-pptx-dita-migration/spec.md`](specs/001-pptx-dita-migration/spec.md)
for the source specification and
[`specs/001-pptx-dita-migration/plan.md`](specs/001-pptx-dita-migration/plan.md)
for the implementation plan.

## Prerequisites

- Python 3.9 or later (CPython, standard interpreter; the air-gapped
  target runs WinPython 3.9.4.0)
- The `python-pptx` and `lxml` packages (`pip install python-pptx lxml`)

### Air-gapped install

`python-pptx` is the runtime baseline dependency — kept deliberately
minimal, though not capped at one (see the constitution, Principle I:
each dependency is weighed against air-gap transfer effort and fragility,
and prep-time/optional tools like the LibreOffice renderer and the
optional Pillow trim live off the runtime path). To install on a host
with no internet access, build a wheelhouse on a development VM that does
have internet access, then copy it across.

On the development VM (pinning to the target's interpreter and OS so
the wheelhouse is self-contained):

```bash
pip download python-pptx lxml \
    --python-version 39 --platform win_amd64 \
    --only-binary=:all: -d wheels/
```

On the air-gapped host:

```bash
pip install --no-index --find-links wheels/ python-pptx lxml
```

`requirements.txt` pins the version with `~=` compatibility so wheelhouse
rebuilds remain predictable.

### Renderer prerequisites (analysis sheets)

Feature 007 adds a **prep-time** stage, `snapshot_analysis_docs.py`,
that renders each Word analysis sheet (`*analysis*.doc` / `.docx`) to a
same-stem `.png` sibling so the generator embeds the analysis table
**inline** instead of leaving a click-to-open link that launches MS Word
mid-lesson. Like DITA-OT, the renderer is an **external tool, not bundled
and not a Python runtime dependency**, and is only needed when a Word
analysis sheet has no rendered `.png` yet.

- **LibreOffice headless (`soffice`)** is the default renderer. On a
  development VM with internet, install LibreOffice normally; for the
  air-gapped PC, download the LibreOffice installer on a connected host
  and transfer it across the air-gap (the same posture as DITA-OT). The
  snapshotter invokes `soffice --headless --convert-to png …` once per
  un-rendered sheet.
- Override the command with `--renderer-cmd` to point at a specific
  `soffice` path or an equivalent converter (e.g. MS Word COM automation
  on a Windows site). Quote a path that contains spaces, e.g.
  `--renderer-cmd "C:\Program Files\LibreOffice\program\soffice.exe"`.
- A few corpus sheets don't follow the `*analysis*` naming convention
  (e.g. `X-aaa.doc`, `V III .doc`) and are therefore skipped by the name
  rule — the extractor then flags their gram rows `analysis image not
  rendered`. Opt them in with repeatable `--extra-name` tokens, matched
  exactly like the built-in `analysis` token (case-insensitive substring
  of the filename stem). The token list is per-corpus configuration, so
  it lives in the **parent calling script**, never in the canonical
  script: `run_pipeline.bat` forwards `%SNAPSHOT_EXTRA_ARGS%`
  (`set SNAPSHOT_EXTRA_ARGS=--extra-name "X-aaa" --extra-name "V III"`),
  and the committed `snapshot.py` wrapper appends the
  `EXTRA_ANALYSIS_NAMES` list from its Config block to `sys.argv`:

  ```python
  EXTRA_ANALYSIS_NAMES = ["X-aaa", "V III"]   # sheets named without "analysis"
  for name in EXTRA_ANALYSIS_NAMES:
      sys.argv += ["--extra-name", name]
  ```
- **Pillow is an *optional* prep-time wheel** used only to trim page
  margins and normalise DPI on the rendered PNG (FR-017). It is imported
  defensively: when Pillow is absent the snapshotter keeps the full-page
  render and logs an INFO line — it never fails and is never required by
  the test suite. To use it, add it to the prep-time wheelhouse
  (`pip download Pillow -d wheels/`); it is **not** installed on the
  pipeline runtime path.

The rendered PNG (and, for a PNG-only sheet, a reverse-wrapped `.docx`,
FR-018) is a **committed source asset**: the snapshotter is idempotent
(it skips any sheet that already has its sibling `.png`), so the renderer
never runs inside the re-runnable generate/publish loop and re-runs are
byte-identical. The snapshotter renders the **first page** and **detects
multi-page sources** — it still produces the page-1 image but logs a
WARNING (and flags the row) rather than silently truncating; the corpus
is single-landscape-page, so the warning is a safety net for the
exception. A render failure or an unavailable renderer is a WARNING that
defers (the run continues, exit 0) and surfaces in `snapshot.log`, the
end-of-run summary, and the analysis row's `warnings` column — the image
then dangles as an intended local `<image>` href, resolved by dropping
the PNG in and re-running.

## Folder structure

| Path | Role |
|---|---|
| `extract.py` `dedupe.py` `write.py` `publish.py` `introspect.py` `snapshot.py` | **Thin REPL wrappers** for the air-gapped target — committed templates that set `sys.argv` and `runpy` a canonical script (see [Running on the air-gapped target machine](#running-on-the-air-gapped-target-machine)). Target-specific paths live only in their Config blocks. |
| `pipeline.py` | **Pipeline orchestrator** (committed template): runs extract → dedupe → write → publish back-to-back in one call, **stopping at the first stage that fails**. `ONLY` in its Config block scopes the whole run to one source folder (a single document); `STAGES` trims which stages run. |
| `scripts/snapshot_analysis_docs.py` | **Prep-time** stage: render each Word `*analysis*` sheet (`.doc`/`.docx`, plus any `--extra-name` opt-ins) to a same-stem `.png` so the analysis table embeds inline; reverse-wrap PNG-only sheets to `.docx` (feature 007). External LibreOffice renderer, optional Pillow trim — neither on the runtime path. |
| `scripts/mock_pptx.py` | Synthetic instructor PPTX generator (Story 4). |
| `scripts/introspect_pptx.py` | Structural-report producer for an instructor PPTX (Story 3). |
| `scripts/extract_to_csv.py` | Walk a content tree and emit the intermediate CSV (Story 2). |
| `scripts/generate_dita.py` | Consume the signed-off CSV and emit DITA topics, copied assets, and ditamaps (Story 1, MVP). |
| `scripts/deduplicate_csv.py` | **Optional** post-process: redirect duplicate large (>10 MiB) assets to a single master copy via the additive `master_png_path` column (feature 006), and renumber within-week gram-number collisions via the additive `target_gram_id` column (feature 008). |
| `scripts/rehydrate_dita.py` | **Optional** reverse step: restore a redirected lofar to a self-contained gram using only the generated DITA (feature 006). |
| `scripts/publish_html.py` | Render the generated DITA tree to HTML5 via DITA-OT for development preview (FR-021). |
| `scripts/vendor/` | Publish-time assets (`gramframe.bundle.js`, operator-console theme) resolved beside `publish_html.py`. |
| `run_pipeline.bat` | Windows orchestrator: snapshot → extract → manual review → generate (Story 6, feature 007). |
| `static/` | **Common pages** (`welcome.dita`, `security.dita`) and their image subfolders, copied into every publication and listed first on each ditamap, ahead of the content nav — the top-level **Week** folders for `main`, the **Grams** folder for the progress tests (feature 010). Override with `--static-root`. |
| `tests/` | Standard-library `unittest` suite (Story 5). |
| `tests/fixtures/` | Tiny committed fixtures (minimal CSV, minimal/malformed GLC). |
| `specs/001-pptx-dita-migration/` | Spec, plan, research, contracts, quickstart, checklists, tasks. |

## Quickstart

```bash
python --version                   # expect 3.9+
python -c "import pptx; print(pptx.__version__)"
python -m unittest discover tests/

# Synthetic data path — no real corpus required
python scripts/mock_pptx.py --out-root mock_corpus/
python scripts/introspect_pptx.py \
    --input "mock_corpus/Instructor Week 1 Grams/Instructor Week 1 Grams.pptx" \
    --out mock_report.txt

# Real or fixture content tree
python scripts/extract_to_csv.py --input-root path/to/content --out extracted.csv
# ...review extracted.csv in Excel...
python scripts/generate_dita.py --csv extracted.csv \
                                --out dita/ \
                                --image-root path/to/content
```

A more detailed walkthrough lives in
[`specs/001-pptx-dita-migration/quickstart.md`](specs/001-pptx-dita-migration/quickstart.md).

## Running on the air-gapped target machine

The delivered pipeline runs on an **air-gapped Windows box with WinPython
3.9.4**. The Start-menu **WinPython interpreter** shortcut opens a Python
REPL, and you drive the pipeline by `exec()`-ing thin **wrapper scripts**
that live at the project root. `run_pipeline.bat` is *not* used here — the
REPL plus wrappers are the interface.

The repository follows the same layout: the wrappers are **committed
templates** at the repo root. Their Config blocks carry illustrative
target paths (`C:\dev\AAAC`, `Z:\dita`, …) that the operator tunes once
per machine; pipeline updates never overwrite the tuned root-level copies
— the release zip ships the wrapper templates under `wrappers\`, so an
extract-over-`ROOT\` upgrade lands them in `ROOT\wrappers\`, never on top
of `ROOT\extract.py` (etc.). See "Getting pipeline updates onto the
target".

### Cold start — every session

The WinPython shortcut opens the REPL with its working directory set to the
**interpreter install dir**, not the project. So each session starts by
changing into the project, then running the stage wrappers in order:

```python
import os
os.chdir(r"C:\dev\aaac")         # the project root on the target — raw string!
os.getcwd()                       # confirm it took

exec(open(r"snapshot.py").read())    # Stage 1 (prep, when Word sheets changed): render analysis sheets -> sibling PNGs
exec(open(r"extract.py").read())     # Stage 3: walk source\ -> extract.csv at ROOT
#   -> open extract.csv in Excel, resolve warnings, save as UTF-8 CSV
exec(open(r"dedupe.py").read())      # optional: renumber within-week gram collisions -> extract.dedupe.csv
exec(open(r"write.py").read())       # Stage 5: generate the DITA tree -> dita\
exec(open(r"publish.py").read())     # Stage 6: HTML preview -> html\ (Oxygen is the production publisher)
```

`introspect.py` is the diagnostic wrapper — a structural report for a single
deck or the whole `source\` tree; reach for it (Stage 2) when a deck
misbehaves.

To run the four core stages in one shot instead of stage-by-stage, use the
**orchestrator** `pipeline.py`. It drives extract → dedupe → write → publish
in order and **fails fast** — if any stage returns a non-zero exit code the
run stops there and the later stages are skipped. Set `ONLY` in its Config
block to a source-folder name to scope the whole run to **one document**
(or `None` for the whole corpus), and trim its `STAGES` tuple to stop early
(e.g. drop `publish` to skip the slow DITA-OT render):

```python
exec(open(r"pipeline.py").read())    # extract -> dedupe -> write -> publish, fail-fast
```

Keep its output paths (`DITA_OUT`, `HTML_OUT`, …) in step with the
`write.py` / `publish.py` Config blocks.

- Use a **raw string** (`r"..."`) or forward slashes in `os.chdir` so the
  backslashes aren't read as escape sequences.
- Do the `os.chdir` **once, by hand** — the wrappers never chdir; their
  relative inputs/outputs (e.g. `extract.csv`) resolve against the cwd you
  set, so don't bake the chdir into them.
- Publishing must target a **mapped drive, not a `\\server\share` UNC path** —
  see [Publishing to HTML](#publishing-to-html-optional).

### After an edit — REPL ergonomics

The wrappers are built so a VS Code edit lands on the next ↑+Enter without
restarting the interpreter:

- They re-read the canonical script from disk each call
  (`runpy.run_path(path, run_name="__main__")`) — no `importlib.reload` dance.
- They bust cross-script import caches (`sys.modules.pop("extract_to_csv", …)`)
  so an edit to one canonical module is seen by the others.
- Canonical scripts exit **REPL-safely**: `if rc and not hasattr(sys, "ps1"):
  sys.exit(rc)` raises `SystemExit` only when run as a real script, never
  killing the REPL.
- To pass a new flag to a canonical script, append to `sys.argv` **in the
  wrapper** — the canonical scripts under `scripts\` are never edited
  per-target; the wrapper is the only place that knows target-specific paths
  and toggles (e.g. `--stub-wav stock.wav`).

### Project layout on the target

```text
ROOT\  (e.g. C:\dev\aaac)
├── extract.py  introspect.py  dedupe.py  write.py  publish.py  snapshot.py   ← thin wrappers (committed templates)
├── pipeline.py          ← orchestrator: extract -> dedupe -> write -> publish, fail-fast (committed template)
├── stock.wav            ← committed silent stub for generate_dita.py --stub-wav
├── source\              ← the real PPTX corpus
├── reports\             ← per-deck introspect reports and scratch output
├── theme\               ← Oxygen overlays for the production publisher (e.g. the GramFrame plugin)
└── scripts\
    ├── pylib\           ← pip install --target lives here (see setup below)
    ├── vendor\          ← publish assets (GramFrame bundle, theme), resolved beside publish_html.py
    └── extract_to_csv.py  generate_dita.py  publish_html.py  …   ← canonical, unmodified
```

`theme\gramframe-oxygen\` is a drop-in overlay (plugin bundle + a `<head>`
fragment) the operator installs once into the Oxygen WebHelp template so the
**production** publish renders interactive grams, mirroring what
`publish_html.py` already does for the dev preview — see that folder's
`README.md`. `theme\oxygen-hide-search\` is a second overlay (one CSS rule)
that hides the useless search box in the **student** edition only, wired in
through the student transformation scenario — see that folder's `README.md`.
Unlike `scripts\vendor\` (dev/CI-only), `theme\` ships in the release zip.

This is the repository's own layout too — clone-for-clone, minus `pylib\`
(installed per-target) and the corpus.

Each wrapper prepends `scripts\pylib` (for `python-pptx`) and `scripts\` (so
the canonical modules can import each other) to `sys.path`, busts the module
caches, sets `sys.argv`, then `runpy.run_path`s the canonical script.

### Getting pipeline updates onto the target — GitHub releases

Every merge to `main` that touches a deliverable file (canonical
`scripts/*.py`, the root wrapper templates, `static/`, `theme/`, `stock.wav`,
`requirements.txt`, this README) runs the *Package release* workflow,
which publishes a GitHub release carrying `aaac-pipeline-vYYYY.MM.DD-N.zip`
and a matching `.sha256` file. The zip mirrors the target layout above —
the canonical `scripts\` tree, `static\`, `theme\` and `stock.wav` at the
root, and the wrapper templates under `wrappers\` — so an update is:

1. On a connected host, download both assets from the latest release
   (far smaller than the full repository zip).
2. After the removable-media transfer, verify on the target:
   `certutil -hashfile aaac-pipeline-….zip SHA256` and compare against the
   `.sha256` file.
3. Extract over `ROOT\` (e.g. `C:\dev\aaac`), overwriting. Your tuned
   root-level wrappers, `source\`, and `reports\` are never touched — the
   archive carries the wrappers under `wrappers\`, not at the root, so the
   update lands fresh templates in `ROOT\wrappers\` and leaves your tuned
   `ROOT\extract.py` (etc.) and their Config blocks alone.
4. **When a wrapper is new or has changed** — most often a brand-new
   `pipeline.py` — copy it up out of `ROOT\wrappers\` to `ROOT\` and tune
   its Config block once. `fc ROOT\wrappers\extract.py ROOT\extract.py`
   shows whether an existing wrapper template gained anything worth
   merging; the canonical `scripts\` it drives has already updated
   underneath it either way.

The unittest suite gates the publish, so a red `main` never cuts a release.
If a deliverable change ever slips through without touching one of the
watched paths, run the workflow by hand (Actions → *Package release* → *Run
workflow*). The `tests\` tree is deliberately not packaged: the tests pin a
repo-shaped layout (`sys.path` points at the repo root), so on the air-gapped
network they run from a full repository copy, not from `ROOT\`.

### First-time setup — WinPython gotchas

WinPython sits under `Program Files\` (read-only to non-admins) on an
AppLocker/WDAC-restricted box. Three traps surface before any pipeline code
runs:

- **User-site install fails silently.** `pip install python-pptx` lands in
  `%APPDATA%\Python\…`, but WinPython ships `ENABLE_USER_SITE = False`, so
  `import pptx` then raises `ModuleNotFoundError`. **Install with
  `pip install --target scripts\pylib python-pptx`** and let the wrappers put
  that dir on `sys.path`.
- **Group-policy DLL block.** A user-folder `lxml`/`Pillow` fails with
  `ImportError: DLL load failed … blocked by group policy` — AppLocker won't
  load `.pyd` binaries from user-writable folders. **Delete the user-folder
  copy** and let WinPython's own pre-trusted build take over
  (`print(etree.__file__)` should point under `Program Files\WinPython\`).
- **Pillow/NumPy mismatch.** A newer Pillow wheel hits
  `numpy.typing has no attribute 'NDArray'` against WinPython's older NumPy —
  same fix: use WinPython's bundled Pillow.

**Rule:** the air-gap wheelhouse should ship **only `python-pptx`**. Source
every binary dependency (`lxml`, `Pillow`, …) from WinPython's pre-trusted
installs, not the user-folder install.

## Stage-by-stage guide

1. **Stage 1 — Mock generation** (optional, for testing).
   `mock_pptx.py` emits a synthetic instructor PPTX with one welcome
   slide and content slides containing 15 gram placeholders each. Both
   shape-level and text-run hyperlink mechanisms are exercised. Use this
   to check the rest of the pipeline before real content is available.

2. **Stage 2 — Introspection.** `introspect_pptx.py` produces a three-section
   report (summary, per-slide, hyperlink targets) for any PPTX. Run this
   against a real instructor presentation to confirm structural
   assumptions before completing the shape-grouping function.

3. **Stage 3 — Extraction.** `extract_to_csv.py` walks the content root,
   classifies each PPTX as `main` or `progress-test-N`, parses the
   linked GLC files, and writes one CSV row per resulting DITA topic.
   The shape-grouping function (`extract_grams_from_slide`) is currently
   a documented stub; the rest of the infrastructure runs end-to-end.

   The `N` in `progress-test-N` is taken from the **single integer in the
   deck name** (`Instructor Progress Test 2 Grams` → `progress-test-2`), so
   the number is stable no matter what subset of the corpus a run covers —
   a `--only` run yields the same number as a full-corpus walk. A test deck
   whose name carries no integer (or more than one) falls back to stable
   encounter-order numbering. Because the number is the deck's own, two
   decks that claim the same integer (e.g. a `… No FR` variant of test 3)
   would both land on `progress-test-3`; keep one canonical deck per number
   in `source\`.

   For fast debug iteration on a single chapter, pass
   `--only "<Chapter Folder Name>"`. The walk is scoped to that subdir
   but the CSV's path schema stays corpus-root-relative, so
   `deduplicate_csv.py` and `generate_dita.py` can keep `--image-root`
   pointing at the corpus root without re-editing. **Don't be tempted
   to narrow `--input-root` instead** — that changes the relpath schema
   and breaks the downstream tools, one folder segment short.

   To build and review **just the main document** without first carving the
   tests out of `source\`, pass `--exclude-tests`: the walk still covers the
   whole corpus but drops every progress-test and final-assessment deck,
   emitting only the `main` publication. It composes with `--only`.

   A live-render gram (the GLC's inner asset is a `.wav`) cannot be rendered
   by GramFrame without a time period, so its `time_end`, `bandwidth`, and
   `bandcentre` view fields are required. Extraction now **fails fast** (writing
   the CSV first so its `warnings` column is inspectable, then exiting non-zero)
   when a `.wav` gram is missing any of them — surfacing the problem here rather
   than late and cryptically in `deduplicate_csv.py`. Fix the offending GLC(s)
   and re-run. For dev/exploration against an incomplete corpus, pass
   `--relaxed` to substitute the default `100` for each missing field and
   complete the run; this is not for deliverable output (GramFrame needs the
   real time period).

4. **Stage 4 — Manual CSV review (technical author).** Open
   `extracted.csv` in Excel. The author should:
   - fill in any empty `vessel_name` they recognise,
   - resolve any rows whose `warnings` column is non-empty,
   - save back as UTF-8 CSV (not `.xlsx`).
   The CSV's UTF-8-with-BOM and CRLF format keeps Excel's encoding
   detection happy. The `wav_treatment` column is deprecated and
   ignored — the generator dispatches on the GLC's inner asset
   extension, no author decision is required.

5. **Stage 5 — DITA generation.** `generate_dita.py` consumes the
   signed-off CSV and writes a self-contained DITA tree: **one topic
   per gram** at `dita/<publication>/<chapter>/gram-NN/gram_NN.dita`
   (the N+1 CSV rows for the gram are merged — Analysis Sheet
   section first, then one section per Lofar in `sequence` order).
   For `main`, the chapter is the **week** (feature 008): a bare-integer
   `target_chapter` of `1`…`4` becomes `dita/main/week-N/`, headed
   `Week N`, and the per-gram `NN` is the effective gram number
   (`target_gram_id` when the dedupe step renumbered a collision, else
   `gram_id`). Each week is a **sub-document**: a chapter topic at
   `dita/main/week-N/week_N.dita` that the ditamap references with the
   week's gram topicrefs nested one tier below it, so the publication
   index lists the weeks and each week's page lists its grams.
   Every referenced asset (PNG, WAV, analysis sheet) is copied beside
   the topic with a stable per-section name (`analysis.png`,
   `lofar-1.png`, `lofar-2-i.png`, ...) so each `href` in the topic
   is a bare filename — no `../` traversal. Each publication's ditamap
   is written **inside its folder** (`dita/<pub>/<pub>.ditamap` with
   folder-relative hrefs — nothing at the `dita/` root except the
   manifest, skipped report, and DITAVAL profile), so a publication
   folder is self-contained and can be opened in Oxygen as-is. Output
   is deterministic: re-running the same CSV
   produces byte-identical files (including the copied assets). If a
   referenced asset is missing on disk, the generator logs a warning
   and still emits the topic with the intended local href — dropping
   the asset in at the expected source path and re-running resolves
   the dangling reference without churning the topic XML.

6. **Stage 6 — Build verification (Oxygen).** Build both the instructor
   profile (no audience exclusion) and the trainee profile (excluding
   `audience="-trainee"`). Vessel names should appear only in the
   instructor build; analysis topics should not appear in the trainee
   build at all.

## CSV column reference

Reviewers should not edit the identity columns
(`publication`, `chapter`, `gram_id`, `topic_type`, `sequence`,
`topic_filename`); the others are author-editable.

Because these columns are pipeline-authored, the tools treat a blank value in a
*required* identity column — `publication`, `gram_id`, `topic_type`, `sequence`,
`topic_filename` (`chapter` is empty-allowed for the progress tests) — as a
hard error rather than coercing it to empty, so a defect surfaces loudly instead
of producing a malformed topic (constitution principle VII, "Strict on
Self-Authored Data"). The `.wav` dedup view fields
(`time_end`/`bandwidth`/`bandcentre`) are likewise required on an audio row,
since they are the key that decides whether two audio grams share a view.

| # | Column | Editable? | Notes |
|---|---|---|---|
| 1 | `publication` | no | `main` or `progress-test-N`. |
| 2 | `chapter` | no | Empty for progress-test rows. |
| 3 | `gram_id` | no | Format `Gram NN`. |
| 4 | `vessel_name` | yes | Instructor-only content. |
| 5 | `topic_type` | no | `glc` or `analysis`. |
| 6 | `sequence` | no | 1-based per gram, scoped per `topic_type`. |
| 7 | `topic_filename` | no | `gram_NN.dita`. Every row of a single gram (one per Lofar plus one analysis) shares this filename; the generator merges the N+1 rows into one DITA topic per gram. |
| 8 | `display_text` | yes (rare) | Human-readable link label from the PPTX run. |
| 9 | `link_href` | yes (rare) | Raw hyperlink URI from the PPTX run; always a `.glc` in the audited corpus. |
| 10 | `glc_path` | yes | Resolved `.glc` path relative to the source folder. |
| 11 | `time_end` | yes | From GLC `bottom_crop`; numeric string. |
| 12 | `bandwidth` | yes | From GLC `bandwidth`; numeric string. Width of the frequency band. |
| 13 | `bandcentre` | yes | From GLC `bandcentre`; numeric string. Centre of the band. The frequency axis is derived from the pair: `freq_start = bandcentre − bandwidth/2`, `freq_end = bandcentre + bandwidth/2` (issue #87). Replaces the former single `freq_end` column. |
| 14 | `png_path` | yes | Asset named inside the GLC, resolved relative to the source folder. `.png`/`.jpg`/`.gif` → embedded inline; `.wav` → GLC-viewer link (the `.glc` + `.wav` pair is copied alongside the topic). |
| 15 | `wav_treatment` | yes | Deprecated; left blank. Retained only for CSV round-trip compatibility. |
| 16 | `warnings` | yes (clear after fix) | Comma-joined recoverable issues. |

Optional, additive columns are appended at the right edge and read with an
empty default, so a CSV without them behaves exactly as before:

| Column | Written by | Notes |
|---|---|---|
| `target_chapter` | extractor / author | **Feature 008/009:** for `main`, the bare-integer **week** (`1`…`4`) a gram lands in. Set automatically from a `Week N` deck title; for a **no-week** deck (e.g. Pub10, Legacy Pub 10) extraction now **even-slices** the deck's grams across the four weeks (`floor(G/4)` per week, remainder to the earliest weeks, in source order) instead of leaving it blank (feature 009). Remains author-editable. The generator expands a bare integer to heading `Week N` and folder `main/week-N/` (`main` carries no per-document tier). Empty falls back to the source `chapter`. |
| `master_png_path` | `deduplicate_csv.py` | Empty = not redirected. Non-empty = the `png_path` of the master copy this row's large duplicated asset should link to instead of copying its own. Only assets strictly over 10 MiB that genuinely duplicate another row are redirected; for `.wav` rows "genuinely duplicate" also requires identical `time_end`/`bandwidth`/`bandcentre` — two `.glc` files windowing the same recording differently are never merged, so neither student view is lost (issues #78, #87). Run `python scripts/deduplicate_csv.py --csv signed.csv --image-root source/ --out signed.dedup.csv`, then `generate_dita.py` against the `.dedup.csv`. Reverse with `python scripts/rehydrate_dita.py --dita dita/ [--gram gram-NN]`. |
| `target_gram_id` | `deduplicate_csv.py` | **Feature 008/009:** empty = use `gram_id` unchanged. Non-empty = the renumbered gram number. The scheme is chosen by `deduplicate_csv.py --main-numbering` (feature 009): **`per-week`** (default) keeps numbering unique *within* each week — native numbers are preserved and only genuine collisions are bumped to one past the week's maximum (the feature-008 behaviour; the same number may recur in different weeks); **`continuous`** numbers `main` as one `1..N` sequence across the four weeks (week N starts past week N-1's maximum). Non-`main` publications always use the per-week rule. `gram_id` is never mutated; the generated folder/file/title use the effective number. If two distinct grams still collide on a week + number, `generate_dita.py` aborts with a per-collision error telling you to run the dedupe step. |

### Editing the CSV in Excel — what can go wrong

The intermediate CSV is written `utf-8-sig` (BOM included), CRLF
line-terminated, with `QUOTE_MINIMAL` quoting (R11). Excel can mangle
all three of those if you "Save As" instead of "Save":

- **BOM stripped** if you re-save as plain CSV without `Unicode (UTF-8)`
  selected — non-ASCII vessel names become mojibake on the next read.
- **Line endings flipped** to LF on macOS or to mixed endings in some
  cross-platform flows. `generate_dita.py` tolerates this on read, but
  the byte-level round-trip invariant in `csv-schema.md` no longer holds.
- **Leading zeros lost** if Excel auto-coerces `Gram 05` style cells.
  Stick to text-cell format for the identity columns.
- **Quoting changes** if Excel decides a free-form column needs quoting
  where the writer did not. Functionally harmless but breaks byte-level
  diffs across runs.

Mitigation: open the CSV with `Data → From Text/CSV → 65001: Unicode (UTF-8)`
and save back with the same encoding; do not edit identity columns
(`publication`, `chapter`, `gram_id`, `topic_type`, `sequence`,
`topic_filename`).

## Corpus drift the extractor handles

The legacy decks mix many authoring styles; `extract_to_csv.py` normalises
the following real patterns, each a live failure before it was handled.
(`extract_grams_from_slide` is the single grouping function both the
extractor and `introspect_pptx.py` share, so a fix here flows to both.)

- **Whitespace-padded titles** ("Battleship&nbsp;&nbsp;&nbsp;" forcing an
  in-shape line break) — whitespace runs collapse to a single space before
  splitting.
- **Vestigial overlays** — a hidden `Group 197` shape stack carries dead
  shape-level links to `file:///…` paths; header detection rejects any
  `file:///` shape link.
- **`.doc` vs `.docx` analysis sheets** — only `.doc/.docx/.png/.jpg/.jpeg`
  are accepted as shape-level header links; a `.glc` at the shape level is
  authoring residue and is skipped.
- **Folder-name grouping, not screen position** — a header pairs with its
  `.glc` candidates by **shared gram folder** in the URL
  (`…/Gram001/… ↔ …/Gram001/…`), URL-decoded and lowercased so `Gram%20001`
  and `Gram 001` collapse to one key.
- **Multi-shape-type clicks** — hyperlinks are read from every descendant
  `p:cNvPr/a:hlinkClick`, covering autoshape, picture, connector and
  graphic-frame wrappers uniformly (picture-shape clicks were previously
  invisible).
- **SmartArt-embedded links** — a gram authored as a SmartArt diagram keeps
  its hyperlinks under `ppt/diagrams/…_rels`; `_slide_diagram_hyperlinks`
  walks those parts (and diagram-to-diagram refs) and threads node text back
  into each `(text, href)`.
- **Split-run labels** — a label split across runs (`"Lofar"` + `" 2"`) is
  rejoined: a single-link paragraph returns the whole paragraph's text.
- **Duplicate integer-only links** — a second link to the same `.glc`
  labelled `"1"`/`"2"` is de-duped per href, keeping the longest label.
- **Phantom / URL-encoded paths** — when a `content_root` is supplied each
  paired `.glc` is checked on disk (missing → dropped with a WARNING), and
  hrefs are `urllib.parse.unquote`d before the lookup so `%20` matches a real
  space.
- **Trailing-letter folder suffix** — a `.glc` in `Gram_11a/` whose header is
  in `Gram_11/` is matched by retrying with the trailing `a` stripped.
- **Office lock files** — `~$Name.pptx` lock files are filtered from the walk.
- **Mixed student/instructor decks** — grams that resolve no `.glc` links are
  hidden from the per-gram view (with the count surfaced); the header-only
  rows are still emitted for downstream visibility.
- **Final-assessment routing** — a deck matching `--final-pattern` (default
  `final assessment`) routes to its own `final-assessment-N` publication
  instead of falling through to `main`.

### Design lessons worth keeping

- **PPTX is just a zip.** When the high-level API misses a link (it will, in
  legacy decks), drop to `zipfile` + `xml.etree.ElementTree`. A zip-grep
  diagnostic is the difference between guessing and knowing where a
  visible-but-unparsed hyperlink lives (`ppt/diagrams/_rels`,
  `ppt/embeddings`, …).
- **Surveys observe; pipelines transform.** `introspect_pptx.py` preserves
  raw structure so drift stays visible; extraction normalises (whitespace,
  vestigial overlays, duplicate links) because the CSV is a clean contract
  for downstream stages.
- **Filesystem existence is a good heuristic.** A `.glc` link to a file that
  isn't on disk is almost always authoring residue, not content — filtering
  on existence removes a surprising amount of drift cleanly.
- **Match observed quirks, don't legislate cleaner authoring.** The
  trailing-`a` fallback, integer-label dedup and split-run recovery are small
  heuristics that fit real patterns rather than demanding re-authoring.

## Running tests

The test suite is split across two layers:

### Python `unittest` — pipeline behaviour and DITA XML output

```bash
python -m unittest discover tests/
```

Standard-library `unittest` discovery, no third-party test framework.
Expected runtime: under one minute on a standard development workstation.

This layer covers `mock_pptx.py`, `introspect_pptx.py`,
`extract_to_csv.py`, the DITA shape emitted by `generate_dita.py`, the
HTML pretty-printer inside `publish_html.py`, and the publisher's
DITA-OT invocation contract (mocked at the `subprocess` boundary).

When a test fails on the air-gapped network:

1. Read the error message — the test ID names the file under test
   (e.g. `tests.test_generate_dita.GenerateDitaTests.test_glc_topic_structure`).
2. Read the per-stage log (`generate.log`, `extract.log`,
   `introspect.log`) created at the project root, which captures DEBUG
   detail from the most recent run.
3. Re-run a single test for shorter feedback:
   `python -m unittest tests.test_generate_dita.GenerateDitaTests.test_glc_topic_structure`.

### Jest — rendered HTML output (spec 003)

```bash
npm install        # one-off, on a host with internet access
npm test
```

The Jest layer (`tests/web/`) verifies the *rendered* HTML output of
the dual-edition publish pipeline. It runs against the live `html/`
tree at the repo root, so it MUST be invoked *after* a successful
`python scripts/publish_html.py` run. The `dita/` and `html/` trees
are **not committed** — CI's web job rebuilds them from the committed
`source/` mock corpus via the full pipeline (extract → dedupe →
generate → publish) before running Jest, and the gh-pages regenerate
workflow publishes the browsable preview. Jest asserts:

- **No leakage of "instructor" content into the student edition** —
  recursive case-insensitive grep over every file and every path
  segment under `html/student/`.
- **Gram heading shape** — every student-edition gram page has a
  heading matching `/^Gram \d+$/` (no vessel name, no separator).
- **URL parity** — every path under `html/instructor/` has a
  corresponding sibling under `html/student/` and vice versa.
- **Shared landing page** — `html/index.html` exposes two
  unambiguous links to the two editions.

Output idempotency (byte-identical HTML across publish runs over an
unchanged source) is verified by the gh-pages regenerate workflow,
which publishes twice and tree-compares the results.

The Jest layer is developer-time only — it is not part of the air-
gapped runtime contract. The Python `unittest` suite remains the
canonical air-gapped test surface.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `NotImplementedError: Shape grouping is not implemented yet.` | Expected pre-handover (FR-015). | Run introspection against a real instructor PPTX, answer the five questions in the stub's docstring, then implement the function. |
| `extract_to_csv.py` exits 0 with empty CSV. | `--input-root` does not contain any `.pptx`. | Verify the path; the walker is recursive. |
| CSV opens with garbled non-ASCII vessel names in Excel. | The file lost its BOM during Save As. | Re-export from Excel via *File → Save As → CSV UTF-8*. |
| `generate_dita.py` warns "Asset missing, href will dangle". | `png_path` (or the WAV's `link_href`) does not resolve to a file under `--image-root`. | Check the path in the CSV row, or pass a different `--image-root`. The topic is emitted with its intended local href anyway — once the asset is in place at the expected source path, re-running the generator copies it without touching the topic XML. |
| `GLC missing bottom_crop` / `bandwidth` / `bandcentre` warnings in CSV. | Source GLC is missing those elements (R6). | On a pre-rendered (`.png`/`.jpg`) gram the author may fill `time_end` / `bandwidth` / `bandcentre` directly or accept the empty defaults (a blank `bandcentre` falls back to a band starting at zero). On a **live-render `.wav`** gram these are required — see next row. |
| `extract_to_csv.py` exits 1: "live-render .wav view field(s) missing — GramFrame cannot render". | A `.wav` gram's GLC has no time period (and/or band fields); GramFrame can't render without them. | Fix the offending GLC(s) listed in the error so they carry `time_end` (and `bandwidth` / `bandcentre`), then re-run. To keep exploring the toolchain against an incomplete corpus, re-run with `--relaxed` to substitute the default `100` (not for deliverable output). |
| `GLC malformed: ...` warning. | Source GLC failed `xml.etree.ElementTree.parse`. | Open the file in a text editor; usually it is truncated. The pipeline will not block on this. |
| Generator produces `skipped.txt` rows. | A GLC row's inner asset is missing or has an extension other than `.png`, `.jpg`, `.gif`, `.wav`. | Drop the asset into the expected source path and re-run, or accept the skip if the row is genuinely unusable. |

## Publishing to HTML (optional)

DITA-OT renders the generated DITA tree to HTML5 for development
sanity-checks. **Oxygen XML Author remains the production publishing
path** — the DITA-OT preview is for inspection only, and is not part of
the automated pipeline.

DITA-OT and its Java runtime are **not bundled** with this project. The
maintainer transfers the installers across the air-gap manually:

1. From an internet-connected machine, download DITA-OT 4.2.4 (or
   newer) from <https://www.dita-ot.org/download> and a matching Java
   runtime (JDK 17+).
2. Verify checksums against the project's vendor records.
3. Transfer to the air-gapped target via the approved removable-media
   procedure.
4. Unzip DITA-OT to a stable location (e.g. `C:\dita-ot-4.2.4`) and
   confirm `bin\dita.bat --version` runs.

Render the generated tree:

```bash
python scripts/publish_html.py --dita-ot /path/to/dita-ot-4.2.4
# Windows: python scripts\publish_html.py --dita-ot C:\dita-ot-4.2.4
```

`publish_html.py` (standard-library only) stages a copy of `dita/`
under `.dita-build/`, injects the DOCTYPE declarations DITA-OT needs
into any file that lacks them (and relocates a legacy root-level
ditamap into its publication folder — current trees already keep each
map at `dita/<pub>/<pub>.ditamap`), and writes HTML5 under
`html/<edition>/<ditamap-stem>/` per ditamap per edition. The staging
directory is cleaned up after each run.

Each publication's `index.html` nav is then pruned to the nodes that
own pages: DITA-OT renders the *entire* map tree on that page, which
for `main` meant every gram in the corpus on one very long page. With
each week now a top-level chapter sub-document, the main index lists
Welcome, Security, and the weeks; each week's own page lists its grams.
Branches under a link-less topichead (the flat progress tests' grams)
are kept — they appear nowhere else.

#### Staging and output on a roomy disk (full-corpus runs)

The staging copy under `.dita-build/` briefly holds a **full copy of
every referenced image** — DITA-OT resolves the bare-filename image
hrefs relative to each topic, so the assets must sit beside the staged
topics. The `html/` output then holds another copy per edition
(instructor **and** student). For the full corpus (~1,000 grams) these
copies can overwhelm a small local disk.

Both locations are configurable. Point `--staged` and `--out` at a
roomy volume such as the provided folder-share:

```bash
python scripts/publish_html.py --dita-ot /path/to/dita-ot-4.2.4 \
    --staged /mnt/share/dita-build --out /mnt/share/html
# Windows: python scripts\publish_html.py --dita-ot C:\dita-ot-4.2.4 ^
#              --staged D:\share\dita-build --out D:\share\html
```

`--staged` is a throwaway, deleted after each run (pass `--keep-staged`
to leave it in place when debugging a failed build — see below); `--out`
holds the deliverable HTML editions. Both default to the current
directory (`.dita-build/` and `html/`) when the flags are omitted.

#### Map a drive — DITA-OT cannot read `\\server\share` (UNC) paths

The "roomy volume" above must be reached through a **mapped drive
letter**, not a raw UNC path. DITA-OT — both the `publish_html.py`
preview and the Oxygen production transform — fails to resolve
`\\server\share\…` inputs: it builds a malformed `file:/server/share/…`
URI (dropping the `//server` authority) and aborts with

```text
[DOTX008E] The resource 'file:/10.159.0.118/Share/…/x.ditamap' cannot
be loaded. … Unable to set input file to job configuration
```

even though the file is present and readable. (The give-away is the
single slash after `file:` — a valid UNC URI is `file://server/share/…`.)

Map the share to a drive letter first, in the **same, non-elevated**
session you publish from:

```bat
net use Z: \\10.159.0.118\Share    REM /persistent:yes to keep it across reboots
```

Then use `Z:\…` paths everywhere — never `\\server\share\…`:

- **`publish_html.py`** — pass drive-letter paths to every directory
  flag: `--dita Z:\Out --staged Z:\dita-build --out Z:\html --dita-ot
  Z:\dita-ot-4.4`.
- **Oxygen (production publisher)** — open the map from `Z:\…`, then in
  the transformation scenario's **Output** tab set the **base**,
  **temporary**, and **output** directories to absolute drive-letter
  paths (e.g. `Z:\dita-temp`, `Z:\html\…`). Duplicate the stock
  scenario first — the built-ins are read-only.

> **Privilege gotcha:** a drive mapped in an Administrator shell is
> invisible to a non-Administrator publisher (and vice-versa). Map the
> drive and launch the publisher — Python or Oxygen — at the same
> privilege level, or the drive letter won't exist for the process and
> you will hit the same "cannot be loaded" error.

#### Debugging a failed build with `--keep-staged`

`publish_html.py` deletes the staged build tree (`--staged`) at the end
of every run, which erases the evidence exactly when a DITA-OT build
fails. Pass `--keep-staged` to leave it in place so you can inspect
what DITA-OT was actually handed — confirm the
`<stem>/<stem>.ditamap` exists and check its exact path:

```bat
python scripts\publish_html.py --dita-ot Z:\dita-ot-4.4 --staged Z:\dita-build --keep-staged
```

The tree is overwritten at the start of the next run, so a kept copy
never goes stale; delete it by hand once you are done inspecting.

### Output layout (spec 003)

Each publish run emits two parallel HTML editions plus a shared
landing page:

```text
html/
├── index.html                        ← shared landing — pick an edition
├── instructor/
│   ├── index.html                    ← publication list, instructor edition
│   ├── main/                         ← DITA-OT render, no audience filter
│   ├── progress-test-1/
│   └── …                             ← one folder per ditamap
└── student/
    ├── index.html                    ← publication list, student edition
    ├── main/                         ← DITA-OT render with --filter=trainee.ditaval
    ├── progress-test-1/
    └── …
```

The instructor edition contains every vessel-name decoration,
Analysis Sheet section, and "Instructor Version" labelling. The
student edition is produced by a second DITA-OT pass with
`dita/trainee.ditaval` excluding every element carrying
`audience="-trainee"`. URL paths below the top-level edition segment
are identical across editions — swapping `instructor/` ↔ `student/`
in any URL reaches the same gram in the other edition.

Pre-existing `html/<publication>/` deep-link URLs from before spec
003 no longer resolve — the shared `html/index.html` is the new
authoritative entry point.

See the full recipe in
[`specs/001-pptx-dita-migration/contracts/dita-topic-schema.md`](specs/001-pptx-dita-migration/contracts/dita-topic-schema.md)
§11 and the dual-edition contracts in
[`specs/003-instructor-student-versions/contracts/`](specs/003-instructor-student-versions/contracts/).

### Common pages and the Grams nav folder (feature 010)

Oxygen renders each **direct child of a ditamap** as a header-bar tab and a
welcome-page tile, so listing grams at the root floods the nav. Every generated
ditamap lives **inside its publication folder** (`dita/<pub>/<pub>.ditamap`,
hrefs relative to that folder — no ditamap at the `dita/` root) and is shaped
per publication kind:

```text
# main — weeks pulled up to the top level
<map>
  <title>…</title>
  <topicref href="welcome.dita"/>           ← common pages, first
  <topicref href="security.dita"/>
  <topicref href="week-1/week_1.dita">      ← each week is a top-level entry
    …week 1's gram topicrefs…
  </topicref>
  <topicref href="week-2/week_2.dita"> … </topicref>
</map>

# progress tests — flat grams stay under one Grams folder
<map>
  <title>…</title>
  <topicref href="welcome.dita"/>
  <topicref href="security.dita"/>
  <topichead><topicmeta><navtitle>Grams</navtitle></topicmeta>
    …gram topicrefs…
  </topichead>
</map>
```

— so the top-level nav is **Welcome · Security · Week 1 · Week 2 · …** for
`main`, and **Welcome · Security · Grams** for each flat progress test. For
`main`, each week is a **sub-document**: a chapter topic (`week-N/week_N.dita`)
whose `<topicref>` nests the week's gram topicrefs one tier below it, so the
rendered publication lists the weeks and each week's own page lists its grams —
rather than every gram landing on one very long page. Because the weeks now sit
at the top level (with no Grams folder to park a weekless gram under), a `main`
row with no week assigned (a Pub10-style deck whose `target_chapter` an analyst
hasn't filled in) is a **fail-fast** error — fill in `target_chapter` and re-run.

The common pages come from `static/` at the repo root: top-level `*.dita`
(Welcome first, Security second, any extras alphabetical) plus their image
subfolders. `generate_dita.py` copies the whole tree into **each** publication
folder and references it by bare filename beside the in-folder ditamap — no
`../`.
Point elsewhere with `--static-root <dir>` (default `static/`); a missing folder
simply omits the pages (logged warning) rather than failing the build. Edit
`static/welcome.dita` and `static/security.dita` in Oxygen like any topic — the
committed copies are mock development content. See [`static/README.md`](static/README.md).

## Known limitations

- **Shape grouping is a documented stub (FR-015).** The
  `extract_grams_from_slide` function in `extract_to_csv.py` raises
  `NotImplementedError` until the introspection report from a real
  instructor presentation answers the five questions in the stub's
  docstring. Every other piece of extractor infrastructure is fully
  implemented and tested.
- **WAV `TBD` rows are skipped, not failed (R8).** They are recorded in
  `skipped.txt`. The pipeline never infers `wav_treatment` — the
  technical author is the sole authority.
- **No automatic output cleanup.** `generate_dita.py` overwrites files
  it produces but does not delete unrelated files in the output tree.
  Use `--clean` to wipe the output tree before generation.
- **Windows orchestrator only.** `run_pipeline.bat` is a Windows batch
  file; on POSIX systems run the Python scripts directly.
- **One third-party dependency.** Only `python-pptx` is required at
  runtime; tests use the standard library only.

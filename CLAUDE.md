# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A defensive five-stage pipeline that migrates legacy AAAC PowerPoint instructor
decks (~15 decks, ~1,000 acoustic "grams") into DITA XML publications matching
the existing pub-9/pub-10 structure, rendered by Oxygen into per-audience
editions. The overriding design constraint: the delivered pipeline must remain
debuggable on an **air-gapped Windows network with no internet and no AI
assistance**. Every design choice (tiny single-purpose scripts, one runtime
dependency, stdlib-only tests, dual-output logging, deterministic output) flows
from that constraint.

## Commands

```bash
# Canonical test suite (air-gapped contract) — stdlib unittest, runs in <1 min
python -m unittest discover tests/

# A single test (fastest feedback loop; the test ID names the file under test)
python -m unittest tests.test_generate_dita.GenerateDitaTests.test_glc_topic_structure

# HTML-output tests (developer-time only) — REQUIRES a prior publish_html.py run
npm install          # one-off, on an internet-connected host
npm test             # Jest, asserts on the rendered html/ tree

# The pipeline (synthetic path needs no real corpus)
python mock_pptx.py --out mock_instructor.pptx
python introspect_pptx.py --input mock_instructor.pptx --out mock_report.txt
python extract_to_csv.py --input-root path/to/content --out extracted.csv
# ...technical author reviews extracted.csv in Excel (UTF-8 CSV, not .xlsx)...
python generate_dita.py --csv extracted.csv --out dita/ --image-root path/to/content
python publish_html.py --dita-ot /path/to/dita-ot-4.2.4   # optional HTML preview
```

There is no build step or linter. `run_pipeline.bat` is a Windows-only
orchestrator (extract → manual review → generate); on POSIX run the scripts
directly. **These are dev-host invocations** — the delivered air-gapped target
is driven differently; see *Operating on the air-gapped target* below.

## Operating on the air-gapped target

The **delivered** interface is neither `run_pipeline.bat` nor bare
`python script.py` (both are dev-host shapes). On the air-gapped WinPython
3.9.4 box the operator drives the pipeline from the **WinPython interpreter
(REPL)** by `exec()`-ing thin **wrapper scripts** that live at the project
root. Full detail is in README.md — "Running on the air-gapped target machine"
(README.md:144) and "Project layout on the target" (README.md:198).

**Cold start, every session.** The REPL opens in the interpreter install dir,
so chdir into the project **once, by hand** (raw string for the backslashes),
then run the wrappers in order:

```python
import os
os.chdir(r"C:\dev\aaac")     # project ROOT on the target (illustrative path)
os.getcwd()                   # confirm it took

exec(open(r"extract.py").read())     # Stage 3: source\  -> reports\extract.csv
exec(open(r"dedupe.py").read())      # optional: renumber within-week gram collisions
exec(open(r"write.py").read())       # Stage 5: signed-off CSV -> dita\
exec(open(r"publish.py").read())     # Stage 6: HTML preview  -> html\
# introspect.py = Stage-2 diagnostic wrapper; reach for it when a deck misbehaves
```

**Target layout** — the wrappers sit one level *above* the canonical scripts:

```text
ROOT\  (e.g. C:\dev\aaac)
├── extract.py  introspect.py  dedupe.py  write.py  publish.py   ← thin wrappers (set sys.argv, runpy the canonical script)
├── stock.wav            ← silent stub for generate_dita.py --stub-wav
├── source\              ← the real PPTX corpus
├── reports\             ← per-run output (extract.csv, logs)
└── scripts\
    ├── pylib\           ← pip install --target python-pptx (WinPython sets ENABLE_USER_SITE = False)
    └── extract_to_csv.py  generate_dita.py  publish_html.py  …   ← canonical, unmodified
```

- **chdir once, by hand** — the wrappers use relative paths and are deliberately
  cwd-independent; don't bake the chdir into them.
- **Publish to a mapped drive, not a `\\server\share` UNC path** — DITA-OT chokes on UNC.
- Target-specific paths/toggles (e.g. `--stub-wav stock.wav`) live **only** in the
  wrapper; the canonical scripts under `scripts\` are never edited per-target.

## Architecture

The pipeline is a flat set of single-purpose scripts at the repo root, each one
stage. Data flows strictly forward; the only branch point is a human.

1. **`mock_pptx.py`** — synthetic instructor PPTX generator (test corpus).
2. **`introspect_pptx.py`** — structural report for a real PPTX.
3. **`extract_to_csv.py`** — walks a content tree, classifies each PPTX as
   `main` or `progress-test-N`, parses linked `.glc` files, emits one CSV row
   per resulting DITA topic.
4. **(human)** — technical author triages the CSV in Excel.
5. **`generate_dita.py`** — consumes the signed-off CSV, emits the DITA tree,
   ditamaps, DITAVAL profiles, manifest, and skipped report.
6. **`publish_html.py`** — renders DITA → HTML via DITA-OT (dev preview only;
   Oxygen is the production publisher).

### The core dispatch (read this before touching the generator)

Each gram has hyperlinks; the `Lofar`-labelled ones **always** point to a `.glc`
config file, which in turn names a sibling asset. **The generator dispatches on
the GLC's inner asset extension, not on any CSV flag:**

- `.png` / `.jpg` (~82%, pre-rendered spectrogram) → embedded inline in the topic.
- `.wav` (~18%, rendered live by the on-PC GLC viewer) → surfaced as a link to
  the `.glc`, with both the `.glc` and `.wav` copied beside the topic.

The `wav_treatment` CSV column is **deprecated and ignored** — retained only for
round-trip compatibility. No author decision selects the treatment.

### One topic per gram

A single gram spans N+1 CSV rows (one per Lofar + one analysis sheet) that all
share a `topic_filename`. The generator **merges** them into one
`gram-NN/gram_NN.dita` topic (Analysis Sheet section first, then one section per
Lofar in `sequence` order). Every referenced asset is copied beside the topic
with a stable name (`analysis.png`, `lofar-1.png`, `lofar-2-i.png`, …) so every
`href` is a bare filename — no `../` traversal.

### The CSV is the human-in-the-loop contract

The intermediate CSV is the handoff between automation and the technical author.
It is written **UTF-8-with-BOM (`utf-8-sig`), CRLF, `QUOTE_MINIMAL`** so Excel's
encoding detection behaves. **Identity columns** (`publication`, `chapter`,
`gram_id`, `topic_type`, `sequence`, `topic_filename`) must not be edited; the
rest are author-editable. New columns are appended at the right edge so older
CSVs read forward-compatibly (a 16-column legacy CSV reads as if the 17th cell
were empty). Full column reference and the Excel "Save As" pitfalls are in
`README.md`.

### Week-based `main` IA and renumbering (feature 008)

`main` is organised into **four week folders**, not one chapter per source deck.
Extraction parses a `Week N` token from a `main` deck's folder title and writes
the bare integer into the editable `target_chapter` column (immutable `chapter`
keeps the full title); `target_doc` is left empty so a week's grams share one
folder. Decks with no week token (Pub10) get a blank `target_chapter` for an
**analyst** to fill in. The generator expands a bare-integer effective chapter
to navtitle `Week N` / slug `week-N` (in `_normalise_chapter`).

Because several decks now share a week, two grams can claim the same number.
`deduplicate_csv.py` **renumbers** the collision: per `(publication, effective
chapter, effective doc)` bucket it walks distinct grams in `(source chapter,
row-order)` order and bumps a taken number to `max+1`, recording it in the
additive `target_gram_id` column (empty = use `gram_id`; `gram_id` is never
mutated). The generator derives every per-gram name from the **effective gram
number** (`target_gram_id or gram_id`). The old letter-suffix auto-disambiguation
is **gone**: an un-renumbered within-week collision is a **fail-fast** error in
`check_row_identity` instructing the operator to run the dedupe step.

### Audiences and editions (feature 004)

Per-gram exclude-audience tags ride a 17th CSV `audience` column → an
`audience="…"` attribute on the gram's **topicref** (never on the topic root) →
DITAVAL profiles the generator emits at build time (`trainee.ditaval`,
`student-own.ditaval`, `student-other.ditaval`). `publish_html.py` runs DITA-OT
once per edition, producing `html/instructor/`, `html/student-own/`, and
`html/student-other/` plus a shared `html/index.html`. Audience consistency
across a gram's rows is enforced fail-fast in the generator.

### Static common pages and the Grams nav folder (feature 010)

Oxygen's webhelp renders every **direct child of a ditamap** as both a
header-bar tab and a welcome-page tile, so a flat list of grams floods the nav.
The generator therefore reshapes every ditamap:

- **Grams are demoted** under a single `<topichead>` (navtitle `Grams`) — one nav
  entry instead of N. For `main` the per-week chapter topicheads nest inside
  Grams; for the progress tests the gram topicrefs sit flat under it.
- **Common static pages** (`welcome.dita`, `security.dita`, then any further
  top-level `*.dita` alphabetically) are prepended as the first topicrefs, so
  every publication opens **Welcome · Security · Grams**.

The pages live in `static/` at the repo root (`--static-root`, default
`static/`): top-level `*.dita` plus their image subfolders. The generator
**copies the whole tree into each publication folder** and references it as
`<publication>/<name>` — the same prefix `publish_html.py`'s stager strips, so
after staging the pages resolve as bare local filenames beside the relocated
ditamap (matching the self-contained-publication, no-`../` invariant). A missing
`static/` degrades gracefully (warn, no pages) per the dangling-asset rule.
Per-publication duplication is intentional: Oxygen publishes each ditamap
independently, so each must be self-contained.

## Invariants to preserve

- **Determinism / idempotency.** Re-running the same CSV produces byte-identical
  output, *including copied binary assets*. Two consecutive publish runs over an
  unchanged source yield byte-identical HTML in every edition. Do not introduce
  timestamps, hash-seeded ordering, or nondeterministic iteration.
- **Minimal, justified dependencies.** The runtime baseline is `python-pptx`
  (pinned `~= 1.0`) — there is no fixed cap, but each added dependency must earn
  its place against the cost of air-gap transfer and added fragility, and should
  prefer a prep-time/optional, gracefully-degrading use over the runtime path
  (as Pillow's defensively-imported trim step does). Tests use the **standard
  library only**. Adding a dependency is a deliberate, PR-justified decision —
  the target is an air-gapped wheelhouse install.
- **Python 3.9 floor.** The air-gapped target is WinPython 3.9.4.0. Use
  `from __future__ import annotations` (type hints evaluate as strings); avoid
  3.10+ syntax and stdlib APIs. Watch for 3.9 gotchas (e.g. `Path.write_text`
  has no `newline` kwarg).
- **Missing assets dangle, they don't crash.** If a referenced asset is absent,
  the generator logs a warning and still emits the topic with its intended local
  href; dropping the asset in and re-running resolves it without churning the XML.
- **Dual logging.** Stages write a DEBUG log at the repo root
  (`generate.log`, `extract.log`, `introspect.log`) alongside console output —
  the primary debugging surface on the air-gapped network.

## Testing layers

- **`tests/` (unittest)** is the canonical, air-gapped test surface covering all
  five scripts plus the DITA shape and the publisher's DITA-OT contract (mocked
  at the `subprocess` boundary).
- **`tests/web/` (Jest)** is developer-time only and asserts on the *rendered*
  `html/` tree — so it must run *after* a successful `publish_html.py`. It checks
  no instructor-content leakage into student editions, gram-heading shape, URL
  parity across editions, and HTML idempotency.

## Known stub

`extract_grams_from_slide` in `extract_to_csv.py` is a documented stub that
raises `NotImplementedError`. It stays stubbed until an introspection report
from a *real* instructor deck answers the five questions in its docstring. All
other extractor infrastructure is implemented and tested.

## Spec-driven workflow

This repo uses Spec Kit. Each feature lives under `specs/NNN-name/` with
`spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`,
`contracts/`, `checklists/`, and `tasks.md`. The project constitution is at
`.specify/memory/constitution.md`. When starting non-trivial work, read the
relevant feature's `spec.md` and `plan.md` first — the contracts under
`contracts/` are the authoritative schemas (CSV, DITA topic, GLC, ditaval).

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
[specs/009-even-week-slicing/plan.md](specs/009-even-week-slicing/plan.md)
<!-- SPECKIT END -->

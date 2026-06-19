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
python scripts/mock_pptx.py --out-root mock_corpus/
python scripts/introspect_pptx.py --input "mock_corpus/Instructor Week 1 Grams/Instructor Week 1 Grams.pptx" --out mock_report.txt
python scripts/extract_to_csv.py --input-root path/to/content --out extracted.csv
# ...technical author reviews extracted.csv in Excel (UTF-8 CSV, not .xlsx)...
python scripts/generate_dita.py --csv extracted.csv --out dita/ --image-root path/to/content
python scripts/publish_html.py --dita-ot /path/to/dita-ot-4.2.4   # optional HTML preview
```

There is no build step or linter. `run_pipeline.bat` is a Windows-only
orchestrator (extract → manual review → generate); on POSIX run the scripts
directly. **These are dev-host invocations** — the delivered air-gapped target
is driven differently; see *Operating on the air-gapped target* below.

## Operating on the air-gapped target

The **delivered** interface is neither `run_pipeline.bat` nor bare
`python scripts/script.py` (both are dev-host shapes). On the air-gapped
WinPython 3.9.4 box the operator drives the pipeline from the **WinPython
interpreter (REPL)** by `exec()`-ing the thin **wrapper scripts** at the
project root. The wrappers are **committed templates** — the repo mirrors
the target layout; only the target paths in each wrapper's Config block
are tuned per machine, and the release zip ships the wrapper templates
under `wrappers\` (not at the archive root) so an extract-over-`ROOT\`
upgrade never overwrites the operator's tuned root-level copies — the
operator copies a new/changed wrapper up out of `ROOT\wrappers\` and
tunes it once. Full detail is in
README.md — "Running on the air-gapped target machine" and "Project
layout on the target".

**Cold start, every session.** The REPL opens in the interpreter install dir,
so chdir into the project **once, by hand** (raw string for the backslashes),
then run the wrappers in order:

```python
import os
os.chdir(r"C:\dev\aaac")     # project ROOT on the target (illustrative path)
os.getcwd()                   # confirm it took

exec(open(r"snapshot.py").read())    # Stage 1 (prep, when Word sheets changed): analysis sheets -> PNGs
exec(open(r"extract.py").read())     # Stage 3: source\  -> extract.csv at ROOT
exec(open(r"dedupe.py").read())      # optional: renumber within-week gram collisions
exec(open(r"write.py").read())       # Stage 5: signed-off CSV -> dita\
exec(open(r"publish.py").read())     # Stage 6: HTML preview  -> html\
# introspect.py = Stage-2 diagnostic wrapper; reach for it when a deck misbehaves
# pipeline.py   = orchestrator: runs extract -> dedupe -> write -> publish in one
#                 call, fail-fast; set ONLY to scope the run to a single document
```

**Target layout** — identical to the repo's own layout; the wrappers sit one
level *above* the canonical scripts:

```text
ROOT\  (e.g. C:\dev\aaac)
├── extract.py  introspect.py  dedupe.py  write.py  publish.py  snapshot.py   ← thin wrappers (set sys.argv, runpy the canonical script)
├── pipeline.py          ← orchestrator: runs the four core stages in sequence, fail-fast
├── stock.wav            ← silent stub for generate_dita.py --stub-wav
├── source\              ← the real PPTX corpus
├── reports\             ← per-deck introspect reports, scratch output
├── theme\               ← Oxygen overlays for the production publisher (GramFrame plugin: theme\gramframe-oxygen\); ships in the release zip
└── scripts\
    ├── pylib\           ← pip install --target python-pptx (WinPython sets ENABLE_USER_SITE = False)
    ├── vendor\          ← publish assets (GramFrame bundle, theme.css), resolved beside publish_html.py (dev/CI-only, not shipped)
    └── extract_to_csv.py  generate_dita.py  publish_html.py  …   ← canonical, unmodified
```

- **chdir once, by hand** — the wrappers never chdir; their relative
  inputs/outputs (e.g. `extract.csv`) resolve against the cwd the operator
  sets, so don't bake the chdir into them.
- **Publish to a mapped drive, not a `\\server\share` UNC path** — DITA-OT chokes on UNC.
- Target-specific paths/toggles (e.g. `--stub-wav stock.wav`) live **only** in the
  wrapper; the canonical scripts under `scripts\` are never edited per-target.

## Architecture

The pipeline is a flat set of single-purpose canonical scripts under
`scripts/`, each one stage, fronted by the thin REPL wrappers at the repo
root. Data flows strictly forward; the only branch point is a human.

1. **`scripts/mock_pptx.py`** — synthetic instructor PPTX generator (test corpus).
2. **`scripts/introspect_pptx.py`** — structural report for a real PPTX.
3. **`scripts/extract_to_csv.py`** — walks a content tree, classifies each PPTX
   as `main` or `progress-test-N`, parses linked `.glc` files, emits one CSV
   row per resulting DITA topic.
4. **(human)** — technical author triages the CSV in Excel.
5. **`scripts/generate_dita.py`** — consumes the signed-off CSV, emits the DITA
   tree, ditamaps, DITAVAL profiles, manifest, and skipped report.
6. **`scripts/publish_html.py`** — renders DITA → HTML via DITA-OT (dev preview
   only; Oxygen is the production publisher).

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
to heading `Week N` / slug `week-N` (in `_normalise_chapter`) and emits each
week as a **top-level chapter sub-document**: a real `main/week-N/week_N.dita`
topic (`emit_main_chapter_topics`) that the main ditamap references at the
**top level of the map** (replacing the former single `Grams` folder), with the
week's gram topicrefs nested one tier below it, **sorted by effective gram
number** (CSV order interleaves decks) — so renderers give every week its own
page listing its grams in order, instead of one enormous flat page of grams.
Because the weeks are now top-level (no `Grams` folder to collect a weekless
gram under), a `main` row with no week assigned is a **fail-fast** error in
`check_main_chapter_assigned` instructing the analyst to fill in
`target_chapter`.

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

### Static common pages and the publication nav (feature 010)

Oxygen's webhelp renders every **direct child of a ditamap** as both a
header-bar tab and a welcome-page tile, so a flat list of grams floods the nav.
The generator therefore shapes every ditamap:

- **Each ditamap lives inside its publication folder** —
  `dita/<pub>/<pub>.ditamap`, never at the `dita/` root — so every href is
  folder-relative and the publication folder is self-contained: open it in
  Oxygen and publish, no path rewriting. `publish_html.py`'s stager copies this
  shape straight through (it still relocates a legacy root-level map and strips
  its `<pub>/` href prefix, for older trees).
- **The content nav differs by publication kind.** For `main`, each per-week
  **chapter sub-document topicref** sits at the **top level** of the map (one
  top-level entry per week, `Week 1` … `Week 4`), with its gram topicrefs one
  tier below — there is no `Grams` folder. For the progress tests (no week
  tier) the gram topicrefs are still **demoted** under a single `<topichead>`
  (navtitle `Grams`) — one nav entry instead of N.
- **Common static pages** (`welcome.dita`, `security.dita`, then any further
  top-level `*.dita` alphabetically) are prepended as the first topicrefs, so
  `main` opens **Welcome · Security · Week 1 · Week 2 · …** and each progress
  test opens **Welcome · Security · Grams**.

The pages live in `static/` at the repo root (`--static-root`, default
`static/`): top-level `*.dita` plus their image subfolders. The generator
**copies the whole tree into each publication folder** and references it by
bare filename beside the in-folder ditamap (matching the
self-contained-publication, no-`../` invariant). A missing
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
  no instructor-content leakage into student editions, gram-heading shape, and
  URL parity across editions. The `dita/` and `html/` trees are **not
  committed**: CI's web job rebuilds both from `source/` via the full pipeline
  before running Jest (plus the dita↔html image-presence cross-checks), and the
  gh-pages regenerate workflow double-publishes and tree-compares to enforce
  the byte-determinism invariant.

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
[specs/010-frequency-bands/plan.md](specs/010-frequency-bands/plan.md)
<!-- SPECKIT END -->

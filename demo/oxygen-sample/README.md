# `oxygen-sample/` — a miniature publication for Oxygen template work

A **small, committed DITA publication** for iterating on the OxygenXML
Responsive WebHelp template and the `theme/` overlays without republishing the
whole corpus.

Publishing is a manual step on a technical author's machine, so the iteration
loop is gated by how long Oxygen takes to render. The full corpus (10 decks,
~350 grams) is far too slow to tune a stylesheet against. This sample is nine
gram pages that still exercise **everything** the real publications do:

- the `main` week IA — two week chapter sub-documents, each a top-level ditamap
  entry with its own gram index;
- the flat `progress-test-1` shape — grams demoted under a single `Grams`
  landing page;
- the common static pages (`Welcome`, `Security`, `7 Questions`);
- inline GramFrame **lofar** stages, `.wav`-backed **WAV** viewer links, and
  instructor-only **analysis sheets** (one with its unreferenced Word original);
- **demon** images leading a gram page at the fixed 0 – 40 Hz band;
- per-week gram renumbering (`target_gram_id`).

## What's here

| Path | Role |
|---|---|
| `sample.csv` | **The source of truth.** A real pipeline artefact: `extract_to_csv.py` output over `source/`, trimmed to nine grams and carried through `deduplicate_csv.py --no-dedupe --main-numbering per-week`. |
| `regenerate.py` | Dev-host runner — rebuilds `dita/` from `sample.csv`. Not one of the air-gapped target wrappers at the repo root, so it never ships in the release zip. |
| `dita/` | **Generated, and committed.** The tree you open in Oxygen. |
| `published/` | Where the hand-published Oxygen output is committed (created by the first publish). |

`dita/` is the one deliberate exception to "the `dita/` tree is not committed":
committing it is what lets the author open Oxygen and publish with no Python
step. `tests/test_oxygen_sample.py` regenerates it into a temp dir and
byte-compares, so it can never silently drift from the generator.

The binary assets under `dita/` are the copies `generate_dita.py` makes beside
each topic (~5.5 MB). The "no committed fixture over 50 KB" convention in
`tests/__init__.py` scopes `tests/fixtures/`, not this folder.

## The roster

Every gram carries an analysis sheet. `main` grams are renumbered contiguously
per week, so the source gram number and the published one differ.

| Publication | Source gram | Published as | What it covers |
|---|---|---|---|
| `main` / Week 1 | Week 1 Gram 1 | `week-1/gram-01` | minimal page; `analysis.docx` copied beside the topic, unreferenced (feature 013) |
| `main` / Week 1 | Week 1 Gram 2 | `week-1/gram-02` | **the stretch page — 2 demons + 5 lofargrams** |
| `main` / Week 1 | Week 1 Gram 13 | `week-1/gram-03` | interleaved media → `Lofar 1`, `WAV 1`, `Lofar 2`, `Lofar 3` (independent counters) |
| `main` / Week 2 | Week 2 Gram 2 | `week-2/gram-01` | four lofars + a Word original |
| `main` / Week 2 | Week 2 Gram 12 | `week-2/gram-02` | a second `.wav` case, in a different week |
| `main` / Week 2 | Week 2 Gram 14 | `week-2/gram-03` | shortest page |
| `progress-test-1` | Grams 1, 10, 11 | `gram-01`, `gram-10`, `gram-11` | the flat nav shape; native numbering (only `main` is renumbered) |

**The stretch page is partly synthetic.** No gram anywhere in `source/` has five
lofars (the mock corpus tops out at four) and no `demon.glc` marker is committed,
so `sample.csv` carries three hand-written rows for Week 1 Gram 2:

- a fifth `glc` row (`sequence=5`) borrowing `Gram 13/Lofar 3 ABC.png` — its
  slugified name, `lofar-3-abc.png`, is distinct from the four already in that
  folder, so nothing is silently overwritten;
- two `demon` rows pointing at the committed [`demon-incoming`](../demon-incoming/)
  fixture images — exactly the pair `ingest_gram_images.py` would have installed,
  with `time_end=232` (the image's pixel height) and the fixed `bandwidth=40` /
  `bandcentre=20`.

The five lofars deliberately carry different `bandwidth`/`bandcentre` values, so
the GramFrame axis rendering varies down the page.

## Regenerating

From the repo root:

```bash
python demo/oxygen-sample/regenerate.py
```

or, equivalently:

```bash
python scripts/generate_dita.py \
    --csv demo/oxygen-sample/sample.csv --out demo/oxygen-sample/dita \
    --image-root . --static-root static --seven-questions 7_questions.png
```

`--image-root` is **the repo root**, not `source/`: every asset cell in
`sample.csv` is a repo-root-relative path, which is what lets the demon rows
reference `demo/demon-incoming/…` alongside the `source/…` spectrograms. Nothing
is duplicated into this folder — the assets already in the repo are the input,
and `generate_dita.py` copies them beside each topic.

The loop is: **edit `sample.csv` → regenerate → commit both.** Then re-publish in
Oxygen and commit `published/`.

## Publishing in Oxygen

Duplicate the two existing `webhelp-responsive` scenarios in
`pptx-transform.xpr` through Oxygen's UI (hand-editing the `.xpr` XML is fiddly)
and point the copies at this tree:

| Setting | Instructor edition | Student edition |
|---|---|---|
| Input | `demo/oxygen-sample/dita/main/main.ditamap` | same |
| DITAVAL | `demo/oxygen-sample/dita/instructor.ditaval` | `demo/oxygen-sample/dita/trainee.ditaval` |
| Output | `${pd}/demo/oxygen-sample/published/instructor` | `${pd}/demo/oxygen-sample/published/student` |
| Temp | under `temp/` (already git-ignored) | under `temp/` |

`demo/oxygen-sample/dita/progress-test-1/progress-test-1.ditamap` is the second
publication; publish it the same way when the flat nav shape needs work.

Note the pre-existing gotcha inherited from those scenarios: `templateRoot` is an
absolute Windows path (`C:/git/pptx-legacy-transform/theme/pptx-transform/`), so
they only work on a machine where the repo sits at that path.

`published/` is **never** verified in CI — Oxygen webhelp output carries build
timestamps and a generated search index, so it is not byte-reproducible, and
Oxygen is not available on the runners.

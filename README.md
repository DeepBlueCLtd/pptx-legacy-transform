# pptx-legacy-transform

A defensive five-stage pipeline that migrates legacy AAAC PowerPoint
instructor presentations into DITA XML publications matching the
existing pub-9/pub-10 structure. The pipeline is built to remain
debuggable on an air-gapped network without internet or AI
assistance: tiny scripts, one third-party dependency, dual-output
logging, and a `unittest`-based test suite.

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

- Python 3.11 or later (CPython, standard interpreter)
- The `python-pptx` package (`pip install python-pptx`)

### Air-gapped install

`python-pptx` is the only third-party runtime dependency. To install it
on a host with no internet access, build a wheelhouse on a
development VM that does have internet access, then copy it across.

On the development VM:

```bash
pip download python-pptx -d wheels/
```

On the air-gapped host:

```bash
pip install --no-index --find-links wheels/ python-pptx
```

`requirements.txt` pins the version with `~=` compatibility so wheelhouse
rebuilds remain predictable.

## Folder structure

| Path | Role |
|---|---|
| `mock_pptx.py` | Synthetic instructor PPTX generator (Story 4). |
| `introspect_pptx.py` | Structural-report producer for an instructor PPTX (Story 3). |
| `extract_to_csv.py` | Walk a content tree and emit the intermediate CSV (Story 2). |
| `generate_dita.py` | Consume the signed-off CSV and emit DITA topics, copied assets, and ditamaps (Story 1, MVP). |
| `deduplicate_csv.py` | **Optional** post-process: redirect duplicate large (>10 MiB) assets to a single master copy via the additive `master_png_path` column (feature 006), and renumber within-week gram-number collisions via the additive `target_gram_id` column (feature 008). |
| `rehydrate_dita.py` | **Optional** reverse step: restore a redirected lofar to a self-contained gram using only the generated DITA (feature 006). |
| `publish_html.py` | Render the generated DITA tree to HTML5 via DITA-OT for development preview (FR-021). |
| `run_pipeline.bat` | Windows orchestrator: extract → manual review → generate (Story 6). |
| `tests/` | Standard-library `unittest` suite (Story 5). |
| `tests/fixtures/` | Tiny committed fixtures (minimal CSV, minimal/malformed GLC). |
| `specs/001-pptx-dita-migration/` | Spec, plan, research, contracts, quickstart, checklists, tasks. |

## Quickstart

```bash
python --version                   # expect 3.11+
python -c "import pptx; print(pptx.__version__)"
python -m unittest discover tests/

# Synthetic data path — no real corpus required
python mock_pptx.py --out mock_instructor.pptx
python introspect_pptx.py --input mock_instructor.pptx --out mock_report.txt

# Real or fixture content tree
python extract_to_csv.py --input-root path/to/content --out extracted.csv
# ...review extracted.csv in Excel...
python generate_dita.py --csv extracted.csv \
                        --out dita/ \
                        --image-root path/to/content
```

A more detailed walkthrough lives in
[`specs/001-pptx-dita-migration/quickstart.md`](specs/001-pptx-dita-migration/quickstart.md).

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
   `gram_id`).
   Every referenced asset (PNG, WAV, analysis sheet) is copied beside
   the topic with a stable per-section name (`analysis.png`,
   `lofar-1.png`, `lofar-2-i.png`, ...) so each `href` in the topic
   is a bare filename — no `../` traversal. Ditamaps, manifest, and
   skipped report are written alongside. Output is deterministic: re-running the same CSV
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
| 12 | `freq_end` | yes | From GLC `bandwidth`; numeric string. |
| 13 | `png_path` | yes | Asset named inside the GLC, resolved relative to the source folder. `.png`/`.jpg`/`.gif` → embedded inline; `.wav` → GLC-viewer link (the `.glc` + `.wav` pair is copied alongside the topic). |
| 14 | `wav_treatment` | yes | Deprecated; left blank. Retained only for CSV round-trip compatibility. |
| 15 | `warnings` | yes (clear after fix) | Comma-joined recoverable issues. |

Optional, additive columns are appended at the right edge and read with an
empty default, so a CSV without them behaves exactly as before:

| Column | Written by | Notes |
|---|---|---|
| `target_chapter` | extractor / author | **Feature 008:** for `main`, the bare-integer **week** (`1`…`4`) a gram lands in. Set automatically from a `Week N` deck title; left empty by extraction for decks with no week token (Pub10), where an **analyst** types the week number per the agreed table. The generator expands a bare integer to heading `Week N` and folder `main/week-N/`. Empty falls back to the source `chapter`. |
| `master_png_path` | `deduplicate_csv.py` | Empty = not redirected. Non-empty = the `png_path` of the master copy this row's large duplicated asset should link to instead of copying its own. Only assets strictly over 10 MiB that genuinely duplicate another row are redirected. Run `python deduplicate_csv.py --csv signed.csv --image-root source/ --out signed.dedup.csv`, then `generate_dita.py` against the `.dedup.csv`. Reverse with `python rehydrate_dita.py --dita dita/ [--gram gram-NN]`. |
| `target_gram_id` | `deduplicate_csv.py` | **Feature 008:** empty = use `gram_id` unchanged. Non-empty = the renumbered gram number assigned when several decks fold into one week folder and two grams claim the same number — the later gram (by source-chapter alphabetical, then row order) is bumped to one past the week's current maximum. `gram_id` is never mutated; the generated folder/file/title use this effective number. Produced by the same `deduplicate_csv.py` run as `master_png_path`. If two distinct grams still collide on a week + number, `generate_dita.py` aborts with a per-collision error telling you to run the dedupe step. |

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
`python publish_html.py` run. It asserts:

- **No leakage of "instructor" content into the student edition** —
  recursive case-insensitive grep over every file and every path
  segment under `html/student/`.
- **Gram heading shape** — every student-edition gram page has a
  heading matching `/^Gram \d+$/` (no vessel name, no separator).
- **URL parity** — every path under `html/instructor/` has a
  corresponding sibling under `html/student/` and vice versa.
- **Shared landing page** — `html/index.html` exposes two
  unambiguous links to the two editions.
- **Output idempotency** — sha256 snapshot of every file under
  `html/` is stable across publish runs against an unchanged DITA
  source.

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
| `GLC missing bottom_crop` / `bandwidth` warnings in CSV. | Source GLC is missing those elements (R6). | Author may either fill `time_end` / `freq_end` directly or accept the empty defaults. |
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
python publish_html.py --dita-ot /path/to/dita-ot-4.2.4
# Windows: python publish_html.py --dita-ot C:\dita-ot-4.2.4
```

`publish_html.py` (standard-library only) stages a copy of `dita/`
under `.dita-build/`, injects the DOCTYPE declarations DITA-OT needs
(the source DITA omits these per the schema contract — Oxygen handles
validation), and writes HTML5 under `html/<edition>/<ditamap-stem>/`
per ditamap per edition. The staging directory is cleaned up after
each run.

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

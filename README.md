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
analysis PNG, and one or more hyperlinked GLC (or WAV) configurations.
The pipeline extracts those into an intermediate CSV, lets the
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
| `generate_dita.py` | Consume the signed-off CSV and emit DITA topics + ditamaps (Story 1, MVP). |
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
   - set `wav_treatment` for every WAV row (`screenshot`, `gaps-lite`,
     or `TBD` if undecided),
   - resolve any rows whose `warnings` column is non-empty,
   - save back as UTF-8 CSV (not `.xlsx`).
   The CSV's UTF-8-with-BOM and CRLF format keeps Excel's encoding
   detection happy.

5. **Stage 5 — DITA generation.** `generate_dita.py` consumes the
   signed-off CSV and writes the DITA tree, ditamaps, manifest, and
   skipped report. Output is deterministic: re-running the same CSV
   produces byte-identical files.

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
| 7 | `topic_filename` | no | `gram_NN_lofarM.dita` or `gram_NN_analysis.dita`. |
| 8 | `display_text` | yes (rare) | Human-readable link label from the PPTX run. |
| 9 | `link_href` | yes (rare) | Raw hyperlink URI from the PPTX run (`.glc`, `.wav`, or other). Source of truth for WAV detection and the stub topic's `xref href`. |
| 10 | `glc_path` | yes | Resolved `.glc` path relative to the source folder; empty for WAV rows. |
| 11 | `time_end` | yes | From GLC `bottom_crop`; numeric string. |
| 12 | `freq_end` | yes | From GLC `bandwidth`; numeric string. |
| 13 | `png_path` | yes | Resolved relative to the source folder. |
| 14 | `wav_treatment` | yes | `screenshot`, `gaps-lite`, `TBD`, or empty. |
| 15 | `warnings` | yes (clear after fix) | Comma-joined recoverable issues. |

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

```bash
python -m unittest discover tests/
```

Standard-library `unittest` discovery, no third-party test framework.
Expected runtime: under one minute on a standard development workstation.

When a test fails on the air-gapped network:

1. Read the error message — the test ID names the file under test
   (e.g. `tests.test_generate_dita.GenerateDitaTests.test_glc_topic_structure`).
2. Read the per-stage log (`generate.log`, `extract.log`,
   `introspect.log`) created at the project root, which captures DEBUG
   detail from the most recent run.
3. Re-run a single test for shorter feedback:
   `python -m unittest tests.test_generate_dita.GenerateDitaTests.test_glc_topic_structure`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `NotImplementedError: Shape grouping is not implemented yet.` | Expected pre-handover (FR-015). | Run introspection against a real instructor PPTX, answer the five questions in the stub's docstring, then implement the function. |
| `extract_to_csv.py` exits 0 with empty CSV. | `--input-root` does not contain any `.pptx`. | Verify the path; the walker is recursive. |
| CSV opens with garbled non-ASCII vessel names in Excel. | The file lost its BOM during Save As. | Re-export from Excel via *File → Save As → CSV UTF-8*. |
| `generate_dita.py` writes some topics but Oxygen reports image not found. | `png_path` is resolved relative to `--image-root` but the file does not exist on disk. | Check the path in the CSV row, or pass a different `--image-root`. |
| `GLC missing bottom_crop` / `bandwidth` warnings in CSV. | Source GLC is missing those elements (R6). | Author may either fill `time_end` / `freq_end` directly or accept the empty defaults. |
| `GLC malformed: ...` warning. | Source GLC failed `xml.etree.ElementTree.parse`. | Open the file in a text editor; usually it is truncated. The pipeline will not block on this. |
| `WAV link; treatment required` warning. | A WAV-targeted link with no `wav_treatment`. | Author sets `wav_treatment` to one of `screenshot`, `gaps-lite`, or `TBD`. |
| Generator produces `skipped.txt` rows. | `wav_treatment=TBD`, empty, or unknown (R8). | Either set the treatment to `screenshot` / `gaps-lite`, or accept the skip. |

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

# Quickstart: PPTX to DITA Migration Pipeline

This walkthrough takes a fresh checkout and produces DITA output from
a synthetic input set, end to end. It is the same path an air-gapped
maintainer would follow to verify the pipeline after any edit.

## 0. Prerequisites

- Python 3.11 or later
- `python-pptx` installed (`pip install python-pptx`, or via the
  air-gapped wheelhouse documented in the README — see R12)
- Windows recommended (the orchestrator script is `.bat`); Linux/macOS
  work for everything except `run_pipeline.bat`

## 1. Verify the environment

```bash
python --version           # expect 3.11+
python -c "import pptx; print(pptx.__version__)"
python -m unittest discover tests/
```

The test suite should report all green. If anything fails before any
edits, fix the environment before continuing.

## 2. Generate a mock instructor PPTX

```bash
python mock_pptx.py --out mock_instructor.pptx
```

Expected output: a ~50–80 KB `mock_instructor.pptx` file containing
one welcome slide and the configured content slides with 15 gram
placeholders each, mixing `.glc` and `.wav` link targets and both
shape-level and text-run hyperlinks.

## 3. Inspect the mock's structure

```bash
python introspect_pptx.py --input mock_instructor.pptx --out mock_report.txt
```

Read `mock_report.txt`. Confirm:

- *Section 1* reports the expected slide count, hyperlink-extension
  counts (`.glc` and `.wav` and `.png`), and shape-level vs text-run
  hyperlink counts.
- *Section 2* shows 15 title rectangles + 15 link text boxes per
  content slide.
- *Section 3* lists every distinct hyperlink target.

This same step against a real instructor PPTX is how the team unblocks
the shape-grouping stub.

## 4. Run the extractor against a tiny fixture tree

The mock generator drops its PPTX in the current directory. To
exercise extraction you also need supporting `.glc` files and PNGs in
the layout the extractor expects. Create a fixture tree and run:

```bash
python extract_to_csv.py --input-root tests/fixtures/sample-content \
                         --out extracted.csv
```

(Until the shape-grouping stub is replaced, this will raise
`NotImplementedError` for any content slide it reaches. The
infrastructure around the stub — argument parsing, walking the
content root, GLC parsing, logging setup — runs to completion before
that point. The unit tests for the GLC parser, the CSV writer, and
path resolution exercise that infrastructure without going through
shape grouping.)

## 5. Review the CSV (Stage 3 — manual)

Open `extracted.csv` in Excel. The reviewer:

- Fills in any empty `vessel_name` they recognise.
- Sets `wav_treatment` for every WAV row (`screenshot`, `gaps-lite`,
  or `TBD` if undecided).
- Resolves any rows whose `warnings` column is non-empty.
- Saves the file as UTF-8 CSV (not `.xlsx`).

## 6. Generate DITA

```bash
python generate_dita.py --csv extracted.csv \
                        --out output/ \
                        --image-root tests/fixtures/sample-content
```

Expected output under `output/`:

- `main/<chapter-slug>/gram_NN_lofarM.dita` for every GLC row
- `main/<chapter-slug>/gram_NN_analysis.dita` for every analysis row
- `progress-test-N/...` flat trees for any test publications
- `ditamaps/main.ditamap` plus one ditamap per progress test
- `manifest.txt` listing every file produced
- `skipped.txt` if any rows were skipped (e.g. `wav_treatment=TBD`)

## 7. Verify idempotency

Run the same generator command a second time. Expect output files to
be byte-identical to the first run (SC-004). On Linux:

```bash
md5sum -c <(find output -type f -exec md5sum {} \; > checksums.txt; cat checksums.txt)
```

On Windows, `certutil -hashfile` per file or a `fc` recursive compare.

## 8. Build verification (Stage 5 — manual, in Oxygen)

In the publishing project, build:

- *Instructor profile* (no audience exclusion): every gram topic
  visible, vessel names visible, analysis topics included.
- *Trainee profile* (excluding `audience="-trainee"`): vessel names
  elided in titles, analysis topics excluded entirely.

Both profiles must build clean (SC-005).

## 9. Run the orchestrator (Windows only)

```bat
run_pipeline.bat W:\training\content
```

The wrapper runs `extract_to_csv.py`, pauses for CSV review, then runs
`generate_dita.py` against `output/`. Any non-zero exit from either
stage propagates to the wrapper's exit code.

---

## Troubleshooting smoke tests

- *Nothing happens, no output*: re-run with stdout visible; the scripts
  always log progress at INFO. If stdout is empty, `setup_logging` was
  not called — likely an early argparse error.
- *`NotImplementedError: Shape grouping...`*: expected pre-handover. Run
  introspection against a real instructor PPTX, then implement the stub
  per the docstring's five questions.
- *CSV opens with garbled non-ASCII vessel names in Excel*: the file
  has lost its BOM. Re-export from Excel via *File → Save As → CSV
  UTF-8*.
- *Generator emits files but Oxygen fails to build*: check the
  generator's log for warnings about missing images and the manifest
  for unexpected files; then run a single-topic Oxygen validation to
  isolate the offending topic.

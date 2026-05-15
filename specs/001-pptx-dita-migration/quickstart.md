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
                        --out dita/ \
                        --image-root tests/fixtures/sample-content \
                        --clean
```

Expected output under `dita/`:

- `main/<chapter-slug>/gram_NN_lofarM.dita` for every GLC row
- `main/<chapter-slug>/gram_NN_lofarM.png` — the referenced image
  asset, copied and renamed to match the topic's stem (FR-022). For
  WAV-stub rows the copied file is the `.wav`; for analysis rows it is
  whatever extension the source carried.
- `main/<chapter-slug>/gram_NN_analysis.dita` for every analysis row
  (plus the matching renamed asset)
- `progress-test-N/...` flat trees for any test publications, with
  topics and assets sitting side-by-side
- `ditamaps/main.ditamap` plus one ditamap per progress test
- `manifest.txt` listing every file produced (topics + assets +
  ditamaps)
- `skipped.txt` if any rows were skipped (e.g. `wav_treatment=TBD`)

If a referenced asset is missing on disk, the generator logs a warning
and still emits the topic with the intended local href. Dropping the
asset in at the expected source path and re-running resolves the
dangling reference without churning the topic XML.

## 7. Verify idempotency

Run the same generator command a second time. Expect output files —
including the copied assets — to be byte-identical to the first run
(SC-004). On Linux:

```bash
md5sum -c <(find dita -type f -exec md5sum {} \; > checksums.txt; cat checksums.txt)
```

On Windows, `certutil -hashfile` per file or a `fc` recursive compare.

## 8. Build verification (Stage 5 — manual, in Oxygen)

In the publishing project, build:

- *Instructor profile* (no audience exclusion): every gram topic
  visible, vessel names visible, analysis topics included.
- *Trainee profile* (excluding `audience="-trainee"`): vessel names
  elided in titles, analysis topics excluded entirely.

Both profiles must build clean (SC-005).

## 9. Optional: HTML preview via DITA-OT

`publish_html.py` automates the DITA-OT invocation documented in the
README's "Publishing to HTML (optional)" section. It stages a copy of
`dita/` under `.dita-build/`, injects the DITA Topic and Map DOCTYPEs
that DITA-OT requires (the source DITA tree omits these per the §0
contract — Oxygen handles validation), promotes each ditamap to the
staged root with hrefs rewritten so DITA-OT does not bury the output,
and writes HTML5 to `html/<ditamap-stem>/`.

```bash
python publish_html.py --dita-ot /path/to/dita-ot-4.2.4
```

The script is a development convenience; Oxygen remains the
production publishing path (FR-021). DITA-OT is not bundled — the
maintainer transfers it across the air-gap manually and supplies its
path via `--dita-ot`.

## 10. Run the orchestrator (Windows only)

```bat
run_pipeline.bat W:\training\content
```

The wrapper runs `extract_to_csv.py`, pauses for CSV review, then runs
`generate_dita.py` against `dita/`. Any non-zero exit from either
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

# Software Specification: PPTX → DITA Migration Pipeline

**Version**: 2  
**Author**: Ian Mayo  
**Date**: May 2026

---

## 1. Project Background

### 1.1 Overview

This work migrates acoustic training content from MS PowerPoint presentations into
DITA XML publications. The target DITA publications use the GramFrame browser-based
spectrogram analysis tool (`gramframe.bundle.js`) to replace the legacy GAPS-Lite
desktop application. GramFrame is the rendering target for every spectrogram in the
published HTML: each gram's `.glc` configurations become `<table class="gram-config">`
elements that the bundle auto-detects on `DOMContentLoaded` and rewrites into
interactive viewers. The exact table shape, DITA source, and bundle-loading
requirements are documented in
[`specs/001-pptx-dita-migration/contracts/gramframe.md`](specs/001-pptx-dita-migration/contracts/gramframe.md).

### 1.2 Development Context — Important

All development happens on an **internet-connected VM** which will subsequently be
moved to an **air-gapped network**. Once on the air-gapped network:

- No internet access
- No Claude Code
- No `pip install`
- Debugging and edits must be done without AI assistance

This means the investment made now in code quality, robustness, test coverage, and
documentation pays dividends later. All scripts should be written defensively, with
comprehensive logging and clear error messages. The goal is that a developer working
alone on the air-gapped network can understand, run, and if necessary modify any
script without external help.

### 1.3 Migration Pipeline

```
Stage 1: Introspection       — validate PPTX structure assumptions
Stage 2: Extraction          — parse all PPTXs + GLC files → intermediate CSV
Stage 3: Review & correction — technical author reviews and signs off CSV (manual)
Stage 4: DITA generation     — generate DITA topics and ditamaps from CSV
Stage 5: QA                  — Oxygen build check and spot review (manual)
```

Stages 1, 2, and 4 are automated (Python scripts). Stages 3 and 5 are manual.

### 1.4 Source Material

- ~35 folders of content on an analyst network (Windows)
- ~15 instructor PPTX presentations (student versions are not processed)
- Each folder contains a PPTX plus subfolders of supporting material
- Supporting material organised either:
  - One subfolder per gram, or
  - One subfolder per 10 grams
- Estimated total grams: ~1,000+

### 1.5 PPTX Structure (Known)

Each PPTX contains:
- A welcome/intro slide (skip this)
- One or more content slides, each containing a **3×5 grid of 15 gram placeholders**

Each gram placeholder consists of:
- A **title shape** (rectangle) containing text like `"Gram 12: Nordik Jockey"`
  - The part after `: ` is the vessel name — instructor-only content
  - In the instructor version, the title shape has a hyperlink to a PNG file
    (a screenshot of the MS Word analysis table)
  - This hyperlink may be a shape-level click action OR a hyperlinked text run
    — **to be confirmed by Stage 1 introspection**
- **1–4 link shapes** beneath the title, each containing hyperlinked text runs
  - Display text differs from filename (e.g. display: `"LOFAR 1"`,
    target: `../gram12/config.glc`)
  - Links point to `.glc` files (XML configuration for GAPS-Lite)
  - A small number may point to `.wav` files instead

### 1.6 GLC File Structure

GLC files are XML. The relevant content:

```xml
<GAPS_Lite_configuration>
  <data_source>
    <filename>W:\some_invalid\path\file.PNG</filename>  <!-- broken path, valid filename -->
    <bitmap_crop_values>
      <top_crop>1</top_crop>
      <bottom_crop>271</bottom_crop>  <!-- time period in seconds → DITA time-end -->
    </bitmap_crop_values>
  </data_source>
  <playback>
    <time_offset>1234567890</time_offset>  <!-- unix epoch -->
  </playback>
  <settings>
    <lofar>
      <bandwidth>400</bandwidth>  <!-- frequency range in Hz → DITA freq-end -->
    </lofar>
  </settings>
</GAPS_Lite_configuration>
```

Key points:
- `filename` path is invalid — strip path, keep filename only
- `bottom_crop` → DITA `time-end`
- `bandwidth` → DITA `freq-end`
- `time-start` and `freq-start` are always `0` (hardcoded)

### 1.7 Target DITA Structure

DITA output uses a gram-config table structure matching existing pub-9/pub-10:

```xml
<topic id="gram_12_lofar1">
  <title>Gram 12<ph audience="-trainee"> - Nordik Jockey</ph></title>
  <body>
    <section>
      <table outputclass="gram-config">
        <tgroup cols="2">
          <tbody>
            <row>
              <entry namest="c1" nameend="c2">
                <image href="gram12.png" placement="break" align="center"/>
              </entry>
            </row>
            <row><entry>time-start</entry><entry>0</entry></row>
            <row><entry>time-end</entry><entry>271</entry></row>
            <row><entry>freq-start</entry><entry>0</entry></row>
            <row><entry>freq-end</entry><entry>400</entry></row>
          </tbody>
        </tgroup>
      </table>
    </section>
  </body>
  <related-links>
    <link href="../gram-index.dita" format="dita"/>
  </related-links>
</topic>
```

Per gram placeholder, the following DITA files are generated:
- One `gram_xx_lofarN.dita` per `.glc` link (each with its own measurements)
- One `gram_xx_analysis.dita` — instructor-only, contains the analysis PNG

### 1.8 Output Folder Structure

Folder structure acts as namespace — no filename prefixing needed:

```
output/
  main.ditamap
  main/
    nordic-fishing-vessels/
      gram_12_lofar1.dita
      gram_12_lofar2.dita
      gram_12_analysis.dita
  progress-test-1.ditamap
  progress-test-1/
    gram_01_lofar1.dita
    gram_01_analysis.dita
  progress-test-2.ditamap
  progress-test-2/
    ...
```

Each ditamap sits at the root next to a similarly-named folder holding
its topics, so `topicref` hrefs in the map are simple forward paths
(no `../` prefix) into that sibling folder.

### 1.9 Intermediate CSV Structure

The CSV produced by Stage 2 has **one row per DITA topic**. A gram placeholder with
4 GLC links and 1 analysis PNG produces 5 rows. The unique key per row is:
`publication + chapter + gram_id + topic_type + sequence`.

| Column | Example | Notes |
|---|---|---|
| `publication` | `main` / `progress-test-1` | |
| `chapter` | `Nordic Fishing Vessels` | Blank for test publications |
| `gram_id` | `Gram 12` | Not globally unique across publications |
| `vessel_name` | `Nordik Jockey` | Instructor-only |
| `topic_type` | `glc` / `analysis` | |
| `sequence` | `1` | For ordering multiple GLC topics per gram |
| `topic_filename` | `gram_12_lofar1.dita` | |
| `display_text` | `LOFAR 1` | Link label from PPTX |
| `glc_path` | `./supporting/gram12/config.glc` | Blank for analysis rows |
| `time_end` | `271` | From GLC `bottom_crop` |
| `freq_end` | `400` | From GLC `bandwidth` |
| `png_path` | `./images/gram12_analysis.png` | |
| `wav_treatment` | `screenshot` / `gaps-lite` / blank | WAV files only; filled by author in Stage 3 |
| `warnings` | `GLC not found` | Blank if clean; multiple warnings comma-separated |

### 1.10 DITA Audience Filtering

Student vs instructor content is controlled by DITA audience filtering at publish
time in Oxygen XML:

- Publish with exclude `audience="-trainee"` → student output (vessel names hidden)
- Publish with no exclusion → instructor output (vessel names visible)

The `<ph audience="-trainee">` element wraps instructor-only content inline:

```xml
<title>Gram 12<ph audience="-trainee"> - Nordik Jockey</ph></title>
```

### 1.11 Progress Test Publications

~4–5 of the source presentations are progress tests. These are clearly identifiable
by filename. They are routed to separate DITA publications (one per test) rather
than chapters in the main publication. Test publications have no chapter level —
they are a flat list of grams.

---

## 2. Scripts to Produce

| Script | Stage | Status |
|---|---|---|
| `mock_pptx.py` | — | Implement fully |
| `introspect_pptx.py` | 1 | Implement fully |
| `extract_to_csv.py` | 2 | Implement with stub for shape-grouping logic |
| `generate_dita.py` | 4 | Implement fully |
| `run_pipeline.bat` | — | Implement fully |
| `README.md` | — | Implement fully |
| `tests/` | — | Implement fully |

**Note on `extract_to_csv.py`**: The logic for grouping shapes into gram placeholders
(associating title shapes with their link text boxes) depends on findings from the
Stage 1 introspection run against real files. This grouping logic must be
implemented as a clearly isolated, clearly documented stub function that raises
`NotImplementedError` with a comment explaining what it needs to do. All surrounding
infrastructure (GLC parsing, CSV writing, path resolution, error handling) should
be fully implemented.

---

## 3. Script 1: `mock_pptx.py`

### 3.1 Purpose

Generate a realistic mock PPTX that faithfully represents the structure of real
instructor presentations, for use in testing the other scripts.

### 3.2 Requirements

**Slide 1: Welcome slide**
- Title text box: `"Welcome to AAAC Training Module 3"`
- Subtitle text box: `"Instructor Version"`
- No gram content

**Slides 2–3: Content slides**
Each must contain exactly 15 gram placeholders in a 3×5 grid (3 rows, 5 columns).

**Each gram placeholder:**

1. A **title rectangle** with text `"Gram NN: Vessel Name"`
   - Use realistic vessel names (e.g. Nordic Fisher, Spirit of Whale Island,
     Barents Explorer, Arctic Surveyor, North Sea Carrier)
   - Attach a **shape-level hyperlink** (click action) pointing to a PNG:
     e.g. `../images/gram01_analysis.png`
   - Shape-level hyperlinks require direct XML manipulation via `._element`
     since python-pptx has no high-level API for this

2. A **link text box** immediately below the title rectangle:
   - 1–4 paragraphs, each a separate hyperlinked text run
   - Display text: `"LOFAR 1"`, `"LOFAR 2"` etc.
   - Targets: `../gramNN/config_1.glc`, `../gramNN/config_2.glc` etc.
   - Use **text-run level hyperlinks** via python-pptx's relationship API

**Variation:**
- Grams 1–10: 1–2 GLC links
- Grams 11–25: 2–3 GLC links
- Grams 26–30: 3–4 GLC links
- Grams 5 and 20: `.wav` link instead of `.glc`
  e.g. `../gram05/audio.wav`

**Layout:**
- Standard widescreen slide: 13.33" × 7.5"
- ~1" margin at top for slide title
- 3×5 grid filling remaining space with small gaps between cells
- Each cell: title rectangle (top ~40% of cell) + link text box (bottom ~60%)

### 3.3 Usage

```bat
python mock_pptx.py --out mock_instructor.pptx
```

---

## 4. Script 2: `introspect_pptx.py`

### 4.1 Purpose

Inspect a PPTX and produce a detailed structural report to confirm assumptions
about shape types, hyperlink mechanisms, and layout consistency.

### 4.2 Output: Section 1 — Summary

- Filename and path
- Total slide count
- All unique hyperlink target extensions found (e.g. `.glc` (42), `.png` (15))
- Count of text-run level vs shape-level hyperlinks
- Any slides where shape count deviates significantly from expected (~32 shapes
  for a 15-gram slide: 15 title rects + 15 link boxes + slide furniture)

### 4.3 Output: Section 2 — Per-slide report

For each slide:
- Slide number and title (if detectable)
- Total shape count
- For each shape:
  - Index, name, type, position in inches (L/T/W/H to 2dp)
  - Full text (truncated to 80 chars)
  - Shape-level hyperlink target (if present)
  - For each paragraph/run: run text and text-run hyperlink target (if present)

### 4.4 Output: Section 3 — Hyperlink summary

Deduplicated list of all hyperlink targets, grouped by file extension, showing
target path, hyperlink type (shape-level / text-run), slide number, shape name.

### 4.5 Hyperlink Detection

Must check both mechanisms for every shape:

**Text-run level:**
```python
rPr = run._r.find(qn('a:rPr'))
hlinkClick = rPr.find(qn('a:hlinkClick'))
rId = hlinkClick.get(qn('r:id'))
target = run._r.part.rels[rId].target_ref
```

**Shape-level (click action):**
```python
sp = shape._element
nvSpPr = sp.find(qn('p:nvSpPr'))
nvPr = nvSpPr.find(qn('p:nvPr'))
hlinkClick = nvPr.find('.//' + qn('a:hlinkClick'))
rId = hlinkClick.get(qn('r:id'))
target = shape.part.rels[rId].target_ref
```

### 4.6 Usage

```bat
python introspect_pptx.py --input mock_instructor.pptx
python introspect_pptx.py --input mock_instructor.pptx --out report.txt
python introspect_pptx.py --input real_presentation.pptx --slides 2,3
```

---

## 5. Script 3: `extract_to_csv.py`

### 5.1 Purpose

Parse all instructor PPTXs and their associated GLC files, producing the
intermediate CSV dataset for human review in Stage 3.

### 5.2 Infrastructure to implement fully

**Command-line interface:**
```bat
python extract_to_csv.py --input-root "W:\training\content" --out extracted.csv
```

**Folder routing:**
- Walk `--input-root` to find all PPTX files
- Identify progress test presentations by filename pattern
  (configurable, e.g. `--test-pattern "progress_test"`)
- Route each PPTX to `publication=main` (with chapter derived from folder/filename)
  or `publication=progress-test-N`

**GLC parsing:**
Fully implement `parse_glc(glc_path)` returning:
```python
{
    "time_end": str,      # from bottom_crop
    "freq_end": str,      # from bandwidth
    "image_filename": str # from filename element, path stripped
}
```
Handle malformed XML gracefully — log warning, return empty values, add to CSV
`warnings` column.

**GLC path resolution:**
Given a relative GLC href from the PPTX, resolve it against the content folder.
Handle both subfolder layouts (per-gram and per-10-grams).
If the file cannot be found, log warning and populate `warnings` column.

**CSV writing:**
Write all rows to the output CSV with the column structure defined in section 1.9.
Populate `warnings` column with comma-separated issues per row.
Emit a summary at the end: total rows, total warnings, list of distinct warning types.

**Logging:**
Use Python's `logging` module. Log to both stdout and a `extract.log` file.
Log at INFO level: each PPTX processed, each GLC resolved.
Log at WARNING level: missing GLC files, malformed XML, unexpected shapes.
Log at ERROR level: any PPTX that cannot be opened or parsed.

### 5.3 Stub: shape grouping logic

The following function must be a clearly documented stub:

```python
def extract_grams_from_slide(slide, slide_num: int) -> list[dict]:
    """
    Extract gram placeholder data from a single slide.

    Returns a list of gram dicts, each containing:
    {
        "gram_id": str,           # e.g. "Gram 12"
        "vessel_name": str,       # e.g. "Nordik Jockey" (may be empty)
        "png_href": str | None,   # href to analysis PNG (instructor version)
        "glc_links": [            # list of GLC link dicts
            {
                "display_text": str,
                "href": str,
            }
        ]
    }

    NOTE: This function is a stub. The shape-grouping logic (identifying which
    shapes are gram titles and which are link boxes, and associating them
    correctly) depends on findings from the Stage 1 introspection run against
    real PPTX files. Once the introspection report is available, implement
    this function based on confirmed shape structure.

    Key questions to answer from introspection before implementing:
    1. Are PNG links on the title shape a shape-level or text-run hyperlink?
    2. Are GLC links always in a separate text box directly below the title?
    3. Are shapes named consistently (e.g. always "Rectangle N" + "TextBox N")?
    4. Is spatial proximity (top/left position) a reliable grouping strategy?
    5. Are there any GROUP shapes wrapping gram content?
    """
    raise NotImplementedError(
        "Shape grouping logic not yet implemented. "
        "Run introspect_pptx.py against real files first and review findings."
    )
```

---

## 6. Script 4: `generate_dita.py`

### 6.1 Purpose

Consume the reviewed and signed-off CSV, generate all DITA topic files and
ditamaps, and write them into the output folder structure.

### 6.2 Requirements

**Command-line interface:**
```bat
python generate_dita.py --csv extracted.csv --out output/ --image-root "W:\training\content"
```

**Per GLC row:** generate `gram_xx_lofarN.dita` with:
- Title using `<ph audience="-trainee">` for vessel name
- gram-config table with time/freq measurements from CSV
- Image reference from `png_path` column (resolved relative to `--image-root`)
- Related links back to gram index

**Per analysis row:** generate `gram_xx_analysis.dita` with:
- Instructor-only image (analysis PNG)
- `audience="-trainee"` on the topic itself or via ditaval

**Per WAV row with `wav_treatment=gaps-lite`:** generate a stub topic with:
- A note that this gram requires GAPS-Lite
- An external link to the `.wav` file
- A `warnings` comment in the XML noting manual review needed

**Per WAV row with `wav_treatment=screenshot`:** treat identically to a PNG row.

**Per WAV row with `wav_treatment=TBD`:** skip generation, log an error, list in
a `skipped.txt` report.

**Ditamap generation:**
- One ditamap per publication (main + each test)
- Main ditamap: chapters as `<topichead>` elements, grams as `<topicref>` children
- Test ditamaps: flat list of `<topicref>` elements (no chapters)
- Audience conditions applied via `<ditavalref>` or inline `@audience` attributes

**Output folder structure:**
Mirror `publication/chapter/` hierarchy as defined in section 1.8.
Create directories as needed.

**Idempotency:**
Re-running the script with the same CSV should produce identical output.
Existing output files are overwritten without warning.

**Logging:**
Log to both stdout and `generate.log`. Report totals at the end:
topics generated, ditamaps generated, skipped rows, any errors.

---

## 7. Script 5: `run_pipeline.bat`

A Windows batch file that runs the full pipeline in sequence:

```bat
@echo off
echo === PPTX to DITA Migration Pipeline ===
echo.

echo [Stage 2] Extracting content from PPTXs...
python extract_to_csv.py --input-root %1 --out extracted.csv
if errorlevel 1 goto error

echo.
echo [Stage 2 complete] Review extracted.csv before continuing.
echo Press any key to proceed to Stage 4 (DITA generation)...
pause > nul

echo [Stage 4] Generating DITA content...
python generate_dita.py --csv extracted.csv --out output\ --image-root %1
if errorlevel 1 goto error

echo.
echo Pipeline complete. Output in output\
goto end

:error
echo ERROR: Pipeline failed. Check logs.
exit /b 1

:end
```

Usage:
```bat
run_pipeline.bat "W:\training\content"
```

---

## 8. Test Suite (`tests/`)

### 8.1 Purpose

Provide a test harness that can be run on the air-gapped network to verify
script behaviour after any edits, without needing Claude or internet access.

### 8.2 Framework

Use Python's built-in `unittest` — no pytest or other test framework, to avoid
additional dependencies.

Run all tests with:
```bat
python -m unittest discover tests/
```

### 8.3 Tests to implement

**`tests/test_mock_pptx.py`**
- Verify `mock_pptx.py` generates a file with the correct slide count
- Verify slide 2 contains exactly 15 gram title shapes and 15 link text boxes
- Verify shape-level hyperlinks exist on title shapes
- Verify text-run hyperlinks exist on link text boxes
- Verify `.wav` links appear on expected grams

**`tests/test_introspect.py`**
- Run introspection against mock PPTX
- Verify summary counts match expected values
- Verify all `.glc`, `.png`, `.wav` links are detected
- Verify both hyperlink types (shape-level, text-run) are reported correctly

**`tests/test_glc_parser.py`**
- Test `parse_glc()` against a minimal valid GLC XML string
- Test handling of missing elements (returns empty string, no exception)
- Test handling of malformed XML (returns empty values, logs warning)
- Test path stripping from `filename` element

**`tests/test_generate_dita.py`**
- Generate DITA from a minimal mock CSV (3–4 rows)
- Verify output files exist in expected locations
- Verify XML is well-formed (parse with `xml.etree.ElementTree`)
- Verify `<ph audience="-trainee">` present when vessel name supplied
- Verify ditamap structure for main publication (with chapters)
- Verify ditamap structure for test publication (flat, no chapters)

### 8.4 Test fixtures

Provide a `tests/fixtures/` directory containing:
- `minimal.glc` — a minimal valid GLC XML file
- `minimal.csv` — a minimal valid CSV with one row of each topic type
- `malformed.glc` — a GLC file with broken XML for error-handling tests

---

## 9. `README.md`

Produce a README covering:

1. **Project context** — brief summary of what this pipeline does and why
2. **Prerequisites** — Python 3.11+, python-pptx, air-gapped installation instructions
3. **Folder structure** — what each script does
4. **Quickstart** — step-by-step instructions from raw PPTXs to DITA output
5. **Stage-by-stage guide** — detailed instructions for each stage including
   what to look for when reviewing the CSV
6. **CSV column reference** — what each column means and valid values
7. **Troubleshooting** — common warnings and how to resolve them
8. **Running tests** — how to run the test suite and interpret results
9. **Known limitations** — shape grouping stub, WAV treatment, etc.

---

## 10. Code Quality Requirements

These apply to all scripts:

- **No global state** — all functions take explicit parameters
- **Type hints** on all function signatures
- **Docstrings** on all functions explaining purpose, parameters, return values,
  and any known limitations
- **Logging not print** — use `logging` module throughout (except `mock_pptx.py`
  which can use print for progress)
- **No silent failures** — every exception must be caught, logged, and either
  re-raised or recorded in the CSV `warnings` column
- **Explicit encoding** — always specify `encoding="utf-8"` on file open/write
- **Path handling** — use `pathlib.Path` throughout, never string concatenation
- **Constants at top** — magic strings and numbers defined as named constants

---

## 11. Delivery

Produce the following files:

```
mock_pptx.py
introspect_pptx.py
extract_to_csv.py
generate_dita.py
run_pipeline.bat
README.md
tests/
  __init__.py
  test_mock_pptx.py
  test_introspect.py
  test_glc_parser.py
  test_generate_dita.py
  fixtures/
    minimal.glc
    minimal.csv
    malformed.glc
```

**Suggested implementation order:**
1. `mock_pptx.py` + `tests/test_mock_pptx.py`
2. `introspect_pptx.py` + `tests/test_introspect.py`
3. `tests/fixtures/` + `tests/test_glc_parser.py`
4. `extract_to_csv.py` (stub for shape grouping)
5. `generate_dita.py` + `tests/test_generate_dita.py`
6. `run_pipeline.bat`
7. `README.md`

After each script, run its tests and confirm they pass before moving on.

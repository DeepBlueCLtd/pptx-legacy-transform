# Software Specification: PPTX Introspection Script & Mock PPTX Generator

## 1. Project Background

### 1.1 Overview

This work is part of a larger migration project: converting acoustic training content
from MS PowerPoint presentations into DITA XML publications. The target DITA
publications will use the GramFrame browser-based spectrogram analysis tool
(gramframe.bundle.js) to replace the legacy GAPS-Lite desktop application.

The migration pipeline has five stages:

```
Stage 1: Introspection       — validate PPTX structure assumptions (THIS TASK)
Stage 2: Extraction          — parse all PPTXs + GLC files → intermediate CSV
Stage 3: Review & correction — technical author reviews and signs off CSV
Stage 4: DITA generation     — generate DITA topics and ditamaps from CSV
Stage 5: QA                  — Oxygen build check and spot review
```

This specification covers **Stage 1 only**: an introspection script and a mock PPTX
generator for testing it.

### 1.2 Source Material

- ~35 folders of content on an analyst network (Windows)
- ~15 instructor PPTX presentations (student versions are not processed)
- Each folder contains a PPTX plus subfolders of supporting material
- Supporting material is organised either:
  - One subfolder per gram, or
  - One subfolder per 10 grams
- Estimated total grams: ~1,000+

### 1.3 PPTX Structure (Known)

Each PPTX contains:
- A welcome/intro slide (ignore this)
- One or more content slides, each containing a **3×5 grid of 15 gram placeholders**

Each gram placeholder consists of:
- A **title shape** (rectangle) containing text like `"Gram 12: Nordik Jockey"`
  - The part after `: ` is the vessel name — instructor-only content
  - In the instructor version, the title shape has a hyperlink to a PNG file
    (a screenshot of the analysis table in MS Word)
  - This hyperlink may be a shape-level click action OR a hyperlinked text run
    — we do not yet know which
- **1–4 link shapes** beneath the title, each containing a hyperlinked text run
  - The display text differs from the filename (e.g. display: "LOFAR 1",
    target: `../gram12/config.glc`)
  - Links point to `.glc` files (XML configuration for GAPS-Lite)
  - A small number may point to `.wav` files instead of `.glc` files
  - Links are expected to be text-run level hyperlinks, but this is unconfirmed

### 1.4 GLC File Structure

GLC files are XML. The relevant elements are:

```xml
<GAPS_Lite_configuration>
  <data_source>
    <filename>W:\some_invalid\path\file.PNG</filename>  <!-- broken path, valid filename -->
    <bitmap_crop_values>
      <top_crop>1</top_crop>
      <bottom_crop>271</bottom_crop>  <!-- time period in seconds -->
    </bitmap_crop_values>
  </data_source>
  <playback>
    <time_offset>1234567890</time_offset>  <!-- unix epoch start date/time -->
  </playback>
  <settings>
    <lofar>
      <bandwidth>400</bandwidth>  <!-- frequency range in Hz, always starting at 0 -->
    </lofar>
  </settings>
</GAPS_Lite_configuration>
```

Key points:
- `filename` contains an invalid Windows path — only the filename itself is usable
- `bottom_crop` → DITA `time-end`
- `bandwidth` → DITA `freq-end`
- `time-start` and `freq-start` are always 0 (hardcoded in DITA output)

### 1.5 Target DITA Structure

The DITA output uses a gram-config table structure (matching pub-9/pub-10):

```xml
<topic id="gram_12_lofar1">
  <title>Gram 12<ph audience="-trainee"> - Nordik Jockey</ph></title>
  <body>
    <section>
      <table outputclass="gram-config">
        <tgroup cols="2">
          <tbody>
            <row><entry namest="c1" nameend="c2"><image href="gram12.png"/></entry></row>
            <row><entry>time-start</entry><entry>0</entry></row>
            <row><entry>time-end</entry><entry>271</entry></row>
            <row><entry>freq-start</entry><entry>0</entry></row>
            <row><entry>freq-end</entry><entry>400</entry></row>
          </tbody>
        </tgroup>
      </table>
    </section>
  </body>
</topic>
```

Per gram placeholder, the following DITA files are generated:
- One `gram_xx_lofarN.dita` per `.glc` link (each with its own measurements)
- One `gram_xx_analysis.dita` — instructor-only, contains the analysis PNG

### 1.6 Output Structure

```
output/
  main/
    nordic-fishing-vessels/
      gram_12_lofar1.dita
      gram_12_lofar2.dita
      gram_12_analysis.dita
  progress-test-1/
    gram_01_lofar1.dita
    gram_01_analysis.dita
  ditamaps/
    main.ditamap
    progress-test-1.ditamap
```

### 1.7 CSV Intermediate Dataset (Stage 2 output, not this task)

For reference, the CSV produced in Stage 2 will have one row per DITA topic:

| Column | Example | Notes |
|---|---|---|
| `publication` | `main` / `progress-test-1` | |
| `chapter` | `Nordic Fishing Vessels` | Blank for test publications |
| `gram_id` | `Gram 12` | Not globally unique |
| `vessel_name` | `Nordik Jockey` | Instructor-only |
| `topic_type` | `glc` / `analysis` | |
| `sequence` | `1` | For ordering multiple GLC topics |
| `topic_filename` | `gram_12_lofar1.dita` | |
| `display_text` | `LOFAR 1` | Link label from PPTX |
| `glc_path` | `./supporting/gram12/config.glc` | Blank for analysis rows |
| `time_end` | `271` | From GLC `bottom_crop` |
| `freq_end` | `400` | From GLC `bandwidth` |
| `png_path` | `./images/gram12_analysis.png` | |
| `wav_treatment` | `screenshot` / `gaps-lite` / blank | WAV files only |
| `warnings` | `GLC not found` | Blank if clean |

---

## 2. This Task

Produce two Python scripts:

1. **`mock_pptx.py`** — generates a realistic mock PPTX for testing
2. **`introspect_pptx.py`** — inspects a PPTX and reports its structure

These scripts will be developed and tested on an internet-connected machine, then
transferred (with the VM) to an air-gapped Windows network for use against real files.

### 2.1 Environment

- **OS**: Windows (primary target), but should also run on Mac/Linux for development
- **Python**: 3.11+
- **Dependencies**: `python-pptx` only (plus its dependencies: `lxml`, `Pillow`)
- **No other third-party libraries**
- Scripts must run from the command line

---

## 3. Script 1: `mock_pptx.py`

### 3.1 Purpose

Generate a realistic mock PPTX file that faithfully represents the structure of the
real instructor presentations. This allows the introspection script to be fully
developed and tested without access to the real (restricted) files.

### 3.2 Requirements

The generated PPTX must contain:

**Slide 1: Welcome slide**
- A title text box containing "Welcome to AAAC Training Module 3"
- A subtitle text box containing "Instructor Version"
- No gram content

**Slides 2–3: Content slides**
Each content slide must contain exactly 15 gram placeholders arranged in a 3×5 grid
(3 rows, 5 columns).

**Each gram placeholder must include:**

1. A **title rectangle** containing text in the format `"Gram NN: Vessel Name"`
   - e.g. `"Gram 01: Nordik Jockey"`, `"Gram 02: Spirit of Whale Island"`
   - Use realistic-sounding vessel names
   - This rectangle must have a **shape-level hyperlink** pointing to a PNG file
     e.g. `../images/gram01_analysis.png`

2. A **link text box** immediately below the title rectangle, containing:
   - 1–4 hyperlinked text runs
   - Each run has display text like `"LOFAR 1"`, `"LOFAR 2"` etc.
   - Each run links to a `.glc` file e.g. `../gram01/config_1.glc`
   - Use **text-run level hyperlinks** (not shape-level)
   - Runs should be on separate lines (separate paragraphs within the text box)

**Variation across grams:**
- Most grams: 1–2 GLC links
- Some grams: 3–4 GLC links
- One or two grams: link to a `.wav` file instead of `.glc`
  e.g. `../gram05/audio.wav`
- Gram numbering: sequential across slides (Gram 01–15 on slide 2,
  Gram 16–30 on slide 3)

**Spatial layout:**
- Slide dimensions: standard widescreen (33706200 EMU × 19050750 EMU,
  i.e. 13.33" × 7.5" at 914400 EMU/inch)
- Leave ~1 inch margin at top for slide title area
- Divide remaining space into a 3×5 grid
- Each gram cell: title rectangle + link text box stacked vertically within the cell
- Leave a small gap between cells

### 3.3 Usage

```
python mock_pptx.py --out mock_instructor.pptx
```

### 3.4 Notes

- The goal is structural fidelity, not visual polish
- Hyperlink targets do not need to exist as real files
- Use `python-pptx`'s relationship API to attach hyperlinks
- For shape-level hyperlinks, you will need to manipulate the XML directly via
  `python-pptx`'s `._element` access, since python-pptx does not expose a
  high-level API for shape click actions

---

## 4. Script 2: `introspect_pptx.py`

### 4.1 Purpose

Inspect a PPTX file and produce a detailed structural report. The report is used to:
- Confirm that assumptions about the PPTX structure are correct
- Identify the exact mechanism used for hyperlinks (text-run vs shape-level)
- Detect unexpected shape types, link targets, or file extensions
- Flag any slides that deviate from the expected 3×5 gram layout

### 4.2 Requirements

The script must produce a plain-text report (printed to stdout and optionally saved
to a file) containing the following sections:

**Section 1: Summary**
- Filename and path
- Total number of slides
- All unique hyperlink target extensions found across the entire file
  (e.g. `.glc`, `.png`, `.wav`)
- Count of text-run level hyperlinks vs shape-level hyperlinks

**Section 2: Per-slide report**

For each slide:
- Slide number and title (if detectable)
- Total shape count
- A list of every shape, each entry showing:
  - Shape index (position in slide.shapes)
  - Shape name (as set in PowerPoint)
  - Shape type (e.g. MSO_SHAPE_TYPE.RECTANGLE, TEXT_BOX, PICTURE, GROUP)
  - Position: left, top, width, height (in inches, rounded to 2dp)
  - Whether the shape has a text frame
  - If it has a text frame: the full text content (truncated to 80 chars)
  - Whether the shape has a **shape-level hyperlink** (click action)
    — if yes: show the target URL/path
  - For each paragraph in the text frame:
    - For each run in the paragraph:
      - Run text
      - Whether the run has a **text-run level hyperlink**
      - If yes: show the target URL/path

**Section 3: Hyperlink summary**

A deduplicated list of all hyperlink targets found, grouped by file extension,
showing:
- The target path
- Whether it was found as a shape-level or text-run level hyperlink
- Which slide and shape it appeared on

### 4.3 Usage

```
python introspect_pptx.py --input mock_instructor.pptx
python introspect_pptx.py --input mock_instructor.pptx --out report.txt
python introspect_pptx.py --input real_presentation.pptx --slides 2,3
```

Optional `--slides` argument accepts a comma-separated list of slide numbers
(1-indexed) to limit the report to specific slides.

### 4.4 Hyperlink Detection

The script must check for hyperlinks in two places:

**Text-run level hyperlinks:**
```python
# Within shape.text_frame.paragraphs[n].runs[n]:
rPr = run._r.find(qn('a:rPr'))
hlinkClick = rPr.find(qn('a:hlinkClick'))
rId = hlinkClick.get(qn('r:id'))
target = run._r.part.rels[rId].target_ref
```

**Shape-level hyperlinks (click actions):**
```python
# On the shape element itself:
sp = shape._element
nvSpPr = sp.find(qn('p:nvSpPr'))
nvPr = nvSpPr.find(qn('p:nvPr'))
hlinkClick = nvPr.find('.//' + qn('a:hlinkClick'))
rId = hlinkClick.get(qn('r:id'))
target = shape.part.rels[rId].target_ref
```

Both mechanisms must be checked for every shape.

### 4.5 Output Format

Use clear plain-text formatting. Example:

```
================================================================================
PPTX INTROSPECTION REPORT
File: mock_instructor.pptx
================================================================================

SUMMARY
-------
Slides: 3
Unique link extensions: .glc (42), .png (15), .wav (2)
Text-run hyperlinks: 44
Shape-level hyperlinks: 15

================================================================================
SLIDE 2
================================================================================
  Shapes: 32

  [00] Name: "Rectangle 3"  Type: RECTANGLE  Pos: L=0.50" T=1.20" W=2.10" H=0.40"
       Text: "Gram 01: Nordik Jockey"
       Shape hyperlink: ../images/gram01_analysis.png
       Paragraphs/runs:
         Para 0 / Run 0: "Gram 01: Nordik Jockey"  [no run hyperlink]

  [01] Name: "TextBox 4"  Type: TEXT_BOX  Pos: L=0.50" T=1.65" W=2.10" H=0.60"
       Text: "LOFAR 1\nLOFAR 2"
       No shape hyperlink
       Paragraphs/runs:
         Para 0 / Run 0: "LOFAR 1"  -> ../gram01/config_1.glc
         Para 1 / Run 0: "LOFAR 2"  -> ../gram01/config_2.glc
  ...

HYPERLINK SUMMARY
-----------------
.glc files (42):
  ../gram01/config_1.glc  [text-run, slide 2, shape "TextBox 4"]
  ../gram01/config_2.glc  [text-run, slide 2, shape "TextBox 4"]
  ...

.png files (15):
  ../images/gram01_analysis.png  [shape-level, slide 2, shape "Rectangle 3"]
  ...

.wav files (2):
  ../gram05/audio.wav  [text-run, slide 2, shape "TextBox 14"]
  ...
```

---

## 5. Testing

Once both scripts are written:

1. Run `mock_pptx.py` to generate `mock_instructor.pptx`
2. Run `introspect_pptx.py` against the mock file
3. Verify the report correctly identifies:
   - Shape-level hyperlinks on title rectangles
   - Text-run hyperlinks on link text boxes
   - `.glc`, `.png`, and `.wav` link targets
   - Correct shape counts per slide
4. Open `mock_instructor.pptx` in PowerPoint (or LibreOffice) to visually
   verify the layout looks plausible

---

## 6. Future Work (not this task)

Once the introspection script has been run against real files and the structural
assumptions confirmed, the following scripts will be developed:

- **`extract_to_csv.py`** — Stage 2: extract all PPTX + GLC data into the
  intermediate CSV
- **`generate_dita.py`** — Stage 4: consume reviewed CSV and generate DITA
  topic files and ditamaps

These will be specified separately once Stage 1 findings are known.

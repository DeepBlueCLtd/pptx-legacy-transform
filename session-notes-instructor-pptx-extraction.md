# Session Notes — Legacy Instructor PPTX Extraction Hardening

Working session on branch `claude/gracious-pascal-Om3h1` (PR #37). The
goal across the session: take the existing `introspect_pptx.py` /
`extract_to_csv.py` / `generate_dita.py` pipeline and harden it
against the variety of real-world authoring styles in the legacy
instructor PPTX corpus, while running the iteration loop on an
air-gapped Windows target with WinPython 3.9.4.

---

## 1. Getting the pipeline running on the target

The target is an air-gapped Windows box with a "WinPython interpreter"
Start-menu shortcut that drops the user straight into a Python REPL.
Several environment-specific obstacles surfaced before any pipeline
code ran:

### 1.1 User-site vs system-site install

`pip install` defaulted to a user-site install
(`%APPDATA%\Python\Python39\site-packages`) because WinPython sits
under `Program Files\` and is read-only to non-admin users. WinPython
ships with `ENABLE_USER_SITE = False`, so the install succeeded but
`import pptx` failed with `ModuleNotFoundError`.

**Resolution:** install with `pip --target <dir> python-pptx` into a
fixed folder next to the scripts (`scripts\pylib`), then prepend that
path to `sys.path` from the runner script. Avoids needing admin
rights, keeps the install self-contained.

### 1.2 Group-policy DLL block

After getting `python-pptx` importable, `from lxml import etree` blew
up with `ImportError: DLL load failed while importing etree: This
program is blocked by group policy`. AppLocker / WDAC was preventing
binary `.pyd` files from loading out of user-writable folders.

**Resolution:** delete the user-folder `lxml/` and let WinPython's
own (system-installed, trusted) `lxml` take over. Confirmed via
`print(etree.__file__)` pointing to `Program Files\WinPython\...`.

### 1.3 Pillow's NumPy dependency

`from PIL.Image` then failed with
`AttributeError: module 'numpy.typing' has no attribute 'NDArray'` —
the newer Pillow wheel referenced a NumPy feature absent in the
older NumPy bundled with WinPython.

**Resolution:** same pattern as `lxml` — delete the user-folder `PIL/`
and let WinPython's bundled Pillow take over.

**Generalisable rule:** on AppLocker-restricted Windows targets, the
wheelhouse should only ship `python-pptx` itself; every binary
dependency (`lxml`, `Pillow`, `XlsxWriter`, etc.) should be sourced
from WinPython's pre-trusted installs, not the user-folder install.

---

## 2. REPL iteration workflow

Because the target uses a REPL (not `python script.py`), iteration
needs different ergonomics. Patterns we settled on:

### 2.0 Setting the working directory in a fresh REPL window

The WinPython Start-menu shortcut drops you into the REPL with the
working directory set to the **interpreter install dir**
(`C:\developer\winpython`), *not* the source tree. So a bare
`exec(open("scripts\run.py").read())` fails with `FileNotFoundError`
until you either pass a long absolute path or change directory first.

Inspect where you are / what you're running:
```python
import os, sys
os.getcwd()        # current working dir (defaults to the WinPython install dir)
sys.executable     # full path to the python.exe actually running
```

Change to the source tree once, then use short relative paths for the
rest of the session:
```python
import os
os.chdir(r"C:\path\to\pptx-legacy-transform")   # raw string: backslashes not escaped
os.getcwd()                                       # confirm it took
exec(open(r"scripts\run.py").read())              # now relative paths work
```

Notes:
- Use a raw string (`r"..."`) or forward slashes (`"C:/path/..."`) so
  backslashes aren't interpreted as escape sequences.
- Do the `os.chdir(...)` manually rather than baking it into `run.py`
  — hard-coding it inside the wrapper defeats the point of relative
  paths and ties the script to one machine's layout.

### 2.1 Re-running after edits

- **`runpy.run_path(path, run_name="__main__")`** re-reads the file
  from disk each call, so VS Code edits land immediately on
  ↑+Enter. No `importlib.reload` dance.
- **`sys.modules.pop("extract_to_csv", None)`** before each run to
  bust the cached cross-script imports — without this, an edit to
  `extract_to_csv` doesn't affect `introspect_pptx`'s view of it
  even when introspect itself is re-read by `runpy`.
- **`exec(open(R).read())`** instead of `runpy.run_path(R, …)` for
  the wrapper script `run.py` — `exec` runs in the REPL's own
  globals, so helpers defined at module level (`cls()`,
  `SCRIPTS`, `SOURCE`) persist for subsequent REPL commands.
- **REPL-safe `sys.exit`**: scripts invoked via `runpy.run_path`
  shouldn't kill the parent REPL. Pattern:
  ```python
  if __name__ == "__main__":
      rc = main()
      if rc and not hasattr(sys, "ps1"):
          sys.exit(rc)
  ```
  `sys.ps1` is only defined in interactive sessions, so this raises
  `SystemExit` only when run as a real script.

Wrapper scripts created:
- `run.py` — single-deck or whole-folder introspect runner.
- `extract.py` — invokes `extract_to_csv.py` with the same path
  setup and cache-bust.
- `dump_rels.py` — diagnostic; lists every hyperlink relationship in
  every slide's `.rels` file by reading the pptx zip directly.
- `find_gram_7.py` — diagnostic template; greps every file inside the
  pptx zip for a needle string, useful when python-pptx can't find a
  hyperlink that's visibly on the slide.

### 2.2 Wrapper-at-root + `scripts/` layout on the target

The target install **does not run the canonical scripts directly**. Layout:

```
ROOT/                     (c:\users\<u>\documents\git\aaac)
├── extract.py            ← wrapper; runs scripts\extract_to_csv.py
├── introspect.py         ← wrapper; runs scripts\introspect_pptx.py
├── dedupe.py             ← wrapper; runs scripts\deduplicate_csv.py
├── write.py              ← wrapper; runs scripts\generate_dita.py
├── publish.py            ← wrapper; runs scripts\publish_html.py
├── stock.wav             ← committed silent stub for --stub-wav (§ below)
├── source\               ← real PPTX corpus
├── reports\              ← per-run output (extract.csv, logs)
└── scripts\
    ├── pylib\            ← `pip install --target` lives here (§1.1)
    ├── extract_to_csv.py
    ├── generate_dita.py
    ├── …                 ← the canonical scripts, unmodified
```

Each wrapper follows the same boilerplate:

```python
import os, sys, runpy
from pathlib import Path

ROOT    = Path(r"c:\users\<u>\documents\git\aaac")
PYLIB   = ROOT / "scripts" / "pylib"
SCRIPTS = ROOT / "scripts"
SOURCE  = ROOT / "source"

for p in (PYLIB, SCRIPTS):                   # pylib for python-pptx (§1.1),
    if str(p) not in sys.path:               # scripts so canonical modules
        sys.path.insert(0, str(p))           # import each other

for mod in ("extract_to_csv", "introspect_pptx", "generate_dita"):
    sys.modules.pop(mod, None)               # bust cross-script caches (§2.1)

WRITE = SCRIPTS / "generate_dita.py"
sys.argv = [str(WRITE), "--csv", "extract.dedupe.csv", "--out", "dita",
            "--image-root", str(SOURCE), "--clean"]
runpy.run_path(str(WRITE), run_name="__main__")
```

Key points when working with this layout:

- **`run_pipeline.bat` is not used on target.** Each stage is invoked by
  `exec(open(r"<root>\write.py").read())` from the REPL (or its sibling
  wrappers), which is why §2.1's REPL ergonomics matter.
- **`stock.wav` at `ROOT`** is the committed silent stub used by
  `generate_dita.py --stub-wav` to slim the DITA tree for cross-system
  transit. Wrappers pass it through via
  `sys.argv += ["--stub-wav", str(ROOT / "stock.wav")]`, gated by a
  module-level `STUB_WAV = True` so the toggle is one edit, not a CLI
  flag the REPL doesn't pass.
- **Passing new flags to a canonical script** = appending to
  `sys.argv` in the wrapper. The canonical scripts under `scripts\`
  are not edited per-target — the wrapper is the only place that knows
  about target-specific paths, toggles, and convenience defaults.
- **Don't bake `os.chdir(ROOT)` into the wrappers** (§2.0). Do it once
  manually in the REPL; the wrappers should be cwd-independent so they
  work whether invoked from REPL, from another script, or from a
  fresh interpreter.


---

## 3. Corpus-drift findings, in order discovered

Each finding is a real authoring pattern in the legacy decks that
broke or misled the pipeline before this session. The fix is
documented next to it.

### 3.1 Whitespace-padded gram titles

Gram labels carry runs of spaces ("Battleship   ") used to force
in-shape line breaks. Naive extraction kept the padding.

**Fix:** `_split_descriptor` collapses any whitespace run to a single
space before splitting.

### 3.2 Vestigial Group-197 overlay

Each slide carries a hidden `Group 197/Rectangle N` shape stack with
shape-level hyperlinks to absolute `file:///D:/Updates/files/.../`
paths — leftover from an earlier authoring iteration before the
files were reorganised. PowerPoint still recognises them as click
targets but they never resolve.

**Fix:** in the header-detection step, reject any shape-level
hyperlink whose URI starts with `file:///`. The live header
rectangles use relative paths.

### 3.3 `.doc` vs `.docx` analysis sheets

Older decks use `.doc` for the analysis sheet, newer ones `.docx` or
a `*ANALYSIS.png` export.

**Fix:** whitelist `.doc / .docx / .png / .jpg / .jpeg` as the only
acceptable shape-level header extensions. A `.glc` shape-level link
is treated as authoring residue and skipped — this also eliminated
a spurious "first gram" that had its `.glc` text-run hyperlink
promoted to the shape level.

### 3.4 Folder-name grouping replaces spatial proximity

The original pairing matched each header with the *closest* `.glc`
candidate below it on the slide. Real decks put `.glc` shapes
beneath the header rectangle in various arrangements, and the
spatial heuristic missed N-of-M when grams had multiple channels.

**Fix:** group `.glc` candidates with their header by **shared
gram folder** in the URL (`.../Gram001/Analysis Sheet.doc` ↔
`.../Gram001/foo.glc`). Folder names are URL-decoded
(`urllib.parse.unquote`) and lowercased for matching, so
`Gram%20001` and `Gram 001` collapse to the same key.

### 3.5 Multi-shape-type click targets

`_shape_level_hyperlink` had been hard-coded to look up
`p:nvSpPr/p:cNvPr/a:hlinkClick`, which only covers autoshape/textbox
(`p:sp`) wrappers. Picture shapes (`p:pic`) keep that XML under
`p:nvPicPr`, so picture-shape clicks were invisible.

**Fix:** search every descendant `p:cNvPr` for an `a:hlinkClick`. The
single walk now covers `p:sp`, `p:pic`, `p:cxnSp`, and
`p:graphicFrame` uniformly.

### 3.6 SmartArt-embedded hyperlinks

One gram per slide in some decks (the "V III .doc" gram, gram 5) is
authored as a **SmartArt diagram**. PowerPoint stores the SmartArt
data tree under `ppt/diagrams/data1.xml` with its own
`ppt/diagrams/_rels/data1.xml.rels` carrying the hyperlinks. None
of python-pptx's shape-level accessors descend into diagram parts,
so these clicks were entirely invisible.

**Fix:** new helper `_slide_diagram_hyperlinks(slide)` walks from
the slide's part through any diagram relationships and recursively
follows diagram-to-diagram refs so both `data1.xml.rels` and
`drawing1.xml.rels` are covered. Hyperlinks become synthetic
candidates that the folder-key match then groups correctly.

SmartArt node text lives in `<dgm:pt>` elements with
`<a:hlinkClick r:id="…"/>` plus inline `<a:t>` runs — the helper
indexes node text by `rId` and threads it through to the
`(text, href)` tuple so labels survive.

**Diagnostic insight:** when a hyperlink is visibly on a slide but
absent from `slideN.xml.rels`, check `ppt/diagrams/_rels/`,
`ppt/embeddings/`, and other parts. The `find_gram_7.py`-style
zip-grep was crucial here.

### 3.7 Split-run labels

PowerPoint authoring sometimes splits a visible label across two
runs: one carries `"Lofar"` plus the hyperlink, a sibling run
carries `" 2"` with no link. Reading only the hyperlinked run gave
us `"Lofar"`; users saw `"Lofar 2"`.

**Fix:** `_run_hyperlinks_in_shape` now checks how many hyperlinks
each paragraph carries. **Single-link paragraphs** return the
combined text of every run in the paragraph as the label.
**Multi-link paragraphs** (mock corpus / multi-channel-in-one-box
pattern) keep per-run text.

### 3.8 Duplicate hyperlinks with integer-only labels

Some grams carry a second hyperlink to the same `.glc` with an
integer-only label ("1", "2") — a leftover from iterative
authoring.

**Fix:** per-header dedup. For each unique href within a gram, keep
the entry whose display text is longest. `"Lofar 2"` (length 7)
wins over `"1"` (length 1).

### 3.9 Phantom links to missing files

Some grams reference `.glc` files that don't exist on disk — the
click does nothing in PowerPoint either, but the link still parses.

**Fix:** optional filesystem validation. When the caller passes a
`content_root`, each paired `.glc` href is checked against disk;
missing targets are dropped with a per-row WARNING. Only kicks in
for callers that supply the root (so unit tests against in-memory
mock corpora are unaffected).

### 3.10 URL-encoded paths vs filesystem reality

`resolve_glc_path` was treating raw href strings as paths, so a
hyperlink to `.../Gram201/100%20-%2030%20Hz.glc` was being looked
up *with the `%20` literals*. After §3.9 landed, this manifested as
the validator dropping every link in real decks.

**Fix:** `urllib.parse.unquote` the href before the filesystem
lookup. The folder-key matcher already did this; the resolver now
does too.

### 3.11 Trailing-letter folder suffix

In one deck, gram 11's `.doc` lived in `Gram_11/` but its `.glc`
files lived in `Gram_11a/`. The folder-key match missed.

**Fix:** when a `.glc`'s folder key doesn't match any header and
ends in `"a"`, retry with the suffix stripped. Logged at INFO
level for traceability. Extensible to other suffix patterns if
more legacy quirks surface.

### 3.12 Office lock files (`~$Foo.pptx`)

PowerPoint/Word create `~$<name>.pptx` lock files alongside open
documents. Same extension, not valid PPTX content, opening one
raises.

**Fix:** `walk_pptxs` filters anything whose basename starts with
`~$`. Same filter applied in `run.py`'s batch walk.

### 3.13 Mixed student/instructor decks

Some decks contain both instructor grams (with resolvable `.glc`
links) and student-only grams (header exists, `.glc` links don't
resolve because the instructor content isn't shipped).

**Fix:** introspect's per-gram view hides grams that resolved no
`.glc` links, surfacing the hidden count at the slide line so the
omission is visible. The extractor itself still emits the
header-only rows so downstream code can know about them.

### 3.14 Final-assessment routing

A deck called "Instructor Progress Final Assessment Grams.pptx" was
falling through to the `main` publication because the filename
doesn't contain "progress test".

**Fix:** `classify_publication` takes an optional `final_pattern`
(default `"final assessment"`) and emits `final-assessment-N`
publication ids. Configurable via `--final-pattern`.

---

## 4. CSV schema work

The CSV grew several columns through the session:

- **`target_ext`** — file extension of whatever the row's hyperlink
  resolves to (`.doc`, `.docx`, `.png`, `.jpg`, `.wav`, etc.).
  Useful for filtering / bucketing by asset format.
- **`target_doc`** — refactoring planning column. Pre-populated by
  the extractor with the source PPTX filename; you edit it in the
  CSV to declare where each gram should land after the refactor.
- **`target_chapter`** — parallel planning column for which
  chapter/week each gram should land in. Defaults to `chapter`.
- **`file_size`** — (merged from `main` branch) size of the asset
  pointed at by `png_path`.

Per-gram ordering: gram numbering uses leading-integer sort
(`"2"` before `"10"`) so the CSV and the introspect report agree on
row order. Sort logic lives in `extract_grams_from_slide`, so both
tools share one source of truth.

---

## 5. Refactoring-aware DITA generation

Implemented in `generate_dita.py` once the CSV schema settled.

**Path layout** now uses the effective columns:
```
{out}/{publication}/[{doc_slug}/]/gram-{NN}[suffix]/
```
where `target_chapter` falls back to `chapter`, and `target_doc` is
slugified and inserted as an extra path segment (omitted when
empty, preserving the pre-refactor layout for unrefactored CSVs).

**Auto-suffix on collision.** Bucket by
`(publication, target_chapter, target_doc, gram_id)`. Distinct gram
identities within a bucket are discriminated by
`(chapter, vessel_name)` — the source chapter plus the vessel
label. When two or more identities collide, each gets a letter
suffix (`a`, `b`, …) applied uniformly to:
- the gram folder name (`gram-05a`)
- the topic filename (`gram_05a.dita`)
- the topic XML id (`gram_05a`)
- the title text (`Gram 5a`)

**Uniqueness check** now fires only when two rows are
indistinguishable on *every* field — a real authoring mistake, not
the legitimate two-grams-share-a-slot case the auto-suffix
handles.

**CSV header validation** is lenient: required columns must be
present, but extras (the new `target_*` set) are tolerated. Old
fixtures keep working, new extractor output also works.

---

## 6. Architectural lessons worth keeping

- **PPTX is just a zip.** When the high-level API misses something
  (and it will, repeatedly, in legacy decks), drop down to
  `zipfile` and `xml.etree.ElementTree` directly. The
  `dump_rels.py` and `find_gram_7.py` diagnostics were each the
  difference between guessing and knowing.
- **Multiple authoring styles coexist within a single corpus.** One
  deck had text-run, picture-shape-level, and SmartArt-embedded
  hyperlinks for different grams on the same slide. The pipeline
  has to handle all three uniformly via the same folder-key
  grouping.
- **Single source of truth for grouping.** Introspect and the
  extractor used to drift; centralising the gram-grouping logic in
  `extract_grams_from_slide` means a fix in one place flows to
  both tools.
- **Surveys observe; pipelines transform.** Introspect's verbose
  output preserves raw structure (so corpus drift is visible).
  Extract normalises whitespace, drops vestigial overlays, dedupes
  duplicate links — because the CSV is a clean contract for
  downstream stages.
- **Filesystem validation as a heuristic.** A `.glc` hyperlink to a
  file that doesn't exist on disk is almost always authoring
  residue, not real content. Filtering on existence catches a
  surprising amount of drift cleanly.
- **Plan for legacy quirks rather than fight them.** The
  trailing-`a` folder fallback, integer-label dedup, split-run
  label recovery, and `.glc`-extension rejection at the header
  step are all in this category — small heuristics that match
  observed authoring patterns rather than trying to legislate
  cleaner authoring.

---

## 7. Branch / PR

All work landed on `claude/gracious-pascal-Om3h1` → PR #37.

Final commits (selection):

| SHA | Subject |
|-----|---------|
| `7a2730c8` | Generator: consume target_doc/target_chapter, auto-suffix gram_id collisions |
| `fc268dd3` | Merge `main` into branch |
| `98aa6f10` | Extractor: add target_doc column for refactoring planning |
| `0975db24` | Extractor: add target_chapter column for refactoring planning |
| `f0924f47` | Extractor: route "final assessment" decks to their own publication |
| `3a5334a9` | Extractor: add target_ext column to the CSV |
| `666b0360` | Extractor: harvest SmartArt node text, fall back to shape text when run text is empty |
| `43c275d0` | Extractor + introspect: walk SmartArt diagram .rels for embedded .glc hyperlinks |
| `beb45e46` | Extractor + introspect: read hyperlinks from any shape wrapper, accept picture-style .glc |
| `9d28b258` | Extractor: associate .glc with header by shared gram folder, not screen position |
| `aeff127f` | Extractor: filter headers by analysis-sheet extension and collect all candidates per gram |
| `0af775c1` | Introspect: gram-focused default view, verbose mode, REPL-safe exit |
| `110dac41` | Extractor: tolerate corpus drift in audited decks |

Test suite remained green across the run: 124 tests passing at the
end of the session.

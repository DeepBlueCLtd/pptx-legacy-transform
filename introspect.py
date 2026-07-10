"""Stage 2 diagnostic wrapper — structural report(s) for PPTX deck(s).

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"introspect.py").read())

Set BATCH_ROOT to a folder to walk every .pptx underneath, or set INPUT
to a single file (and leave BATCH_ROOT = None). Reports land in
reports\\, one .txt per deck. Reach for this when a deck misbehaves in
extraction — set VERBOSE = True for per-slide shape and hyperlink
detail. Target-specific paths live only in the Config block below.
"""
import os, sys, runpy
from pathlib import Path

ROOT    = Path(r"C:\dev\AAAC")
PYLIB   = ROOT / "scripts" / "pylib"
SCRIPTS = ROOT / "scripts"
SOURCE  = ROOT / "source"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

def cls():
    os.system("cls")

for p in (PYLIB, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

for mod in ("extract_to_csv", "introspect_pptx", "deduplicate_csv",
            "generate_dita", "publish_html", "rehydrate_dita",
            "snapshot_analysis_docs", "ingest_gram_images", "mock_pptx"):
    sys.modules.pop(mod, None)

# ---- Config ----------------------------------------------------
INTROSPECT = SCRIPTS / "introspect_pptx.py"
# Single-deck mode: point INPUT at one .pptx (leave BATCH_ROOT = None).
INPUT      = SOURCE / "Instructor Week 1 Grams" / "Instructor Week 1 Grams.pptx"
# Batch mode: a folder to walk every .pptx underneath, e.g. SOURCE.
BATCH_ROOT = None
VERBOSE    = False
# ----------------------------------------------------------------

def _introspect(pptx, out):
    argv = [str(INTROSPECT), "--input", str(pptx), "--out", str(out)]
    if VERBOSE:
        argv.append("--verbose")
    sys.argv = argv
    runpy.run_path(str(INTROSPECT), run_name="__main__")

if BATCH_ROOT is not None:
    decks = [p for p in sorted(Path(BATCH_ROOT).rglob("*.pptx"))
             if not p.name.startswith("~$")]
    print("introspecting %d deck(s) under %s" % (len(decks), BATCH_ROOT))
    for deck in decks:
        _introspect(deck, REPORTS / (deck.stem + ".txt"))
else:
    _introspect(INPUT, REPORTS / ("introspect_" + INPUT.stem + ".txt"))

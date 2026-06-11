"""Dedupe wrapper (optional, between extract and write) — renumber
within-week gram collisions.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"dedupe.py").read())

Reads extract.csv from the cwd, records renumbered grams in the additive
target_gram_id column, and writes extract.dedupe.csv beside it (plus
dedup.log). gram_id is never mutated. See scripts\\deduplicate_csv.py
--main-numbering (per-week | continuous) for the main-pub numbering
policy. Target-specific paths live only in the Config block below.
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
            "snapshot_analysis_docs", "mock_pptx"):
    sys.modules.pop(mod, None)

# ---- Config ----------------------------------------------------
DEDUPE = SCRIPTS / "deduplicate_csv.py"
# ----------------------------------------------------------------

sys.argv = [
    str(DEDUPE),
    "--csv", "extract.csv",
    "--image-root", str(SOURCE),
    "--out", "extract.dedupe.csv",
]
runpy.run_path(str(DEDUPE), run_name="__main__")

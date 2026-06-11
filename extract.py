"""Stage 3 wrapper — walk source\\ and write the intermediate CSV.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"extract.py").read())

Re-reads scripts\\extract_to_csv.py from disk on every call, so an edit
to the canonical script lands on the next up-arrow + Enter without
restarting the REPL. Writes extract.csv at ROOT (triage it in Excel,
save back as UTF-8 CSV) and extract.log in the cwd. Target-specific
paths and toggles live only in the Config block below — never edit the
canonical script per-target.
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
EXTRACT = SCRIPTS / "extract_to_csv.py"
# ----------------------------------------------------------------

sys.argv = [
    str(EXTRACT),
    "--input-root", str(SOURCE),
    "--out", str(ROOT / "extract.csv"),
    # Fast per-chapter iteration: scope the walk to one deck folder. CSV
    # paths stay corpus-root-relative, so downstream flags don't move:
    # "--only", "Instructor Week 1 Grams",
]
runpy.run_path(str(EXTRACT), run_name="__main__")

"""Stage 1 wrapper — snapshot Word analysis sheets to PNG beside each deck.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"snapshot.py").read())

Walks source\\ for .doc/.docx analysis sheets and renders each to a
sibling PNG (skipping up-to-date ones), logging to snapshot.log in the
cwd. The renderer defaults to "soffice" on PATH; uncomment the
--renderer-cmd line below to point at an explicit LibreOffice install.
Add "--dry-run" to sys.argv to list the work without rendering.
Target-specific paths live only in the Config block below.
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
SNAPSHOT = SCRIPTS / "snapshot_analysis_docs.py"
# ----------------------------------------------------------------

sys.argv = [
    str(SNAPSHOT),
    "--content-root", str(SOURCE),
    # "--renderer-cmd", r'"C:\Program Files\LibreOffice\program\soffice.exe"',
]
runpy.run_path(str(SNAPSHOT), run_name="__main__")

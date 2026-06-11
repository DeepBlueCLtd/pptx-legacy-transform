"""Stage 6 wrapper — render the DITA tree to per-edition HTML via DITA-OT.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"publish.py").read())

Runs DITA-OT once per audience edition and writes the shared landing
page. All four locations below must be on a mapped drive, not a
\\\\server\\share UNC path — DITA-OT chokes on UNC. The staging folder
briefly holds a full copy of every image; add "--keep-staged" to
sys.argv to inspect what DITA-OT was handed when a build fails.
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
PUBLISH        = SCRIPTS / "publish_html.py"
DITA_OUT       = Path(r"Z:\dita")
DITA_OT        = Path(r"Z:\dita-ot-4.4")
STAGING_FOLDER = Path(r"Z:\dita-build")
HTML_OUT       = Path(r"Z:\html")
# ----------------------------------------------------------------

sys.argv = [
    str(PUBLISH),
    "--dita", str(DITA_OUT),
    "--out", str(HTML_OUT),
    "--dita-ot", str(DITA_OT),
    "--staged", str(STAGING_FOLDER),
]
runpy.run_path(str(PUBLISH), run_name="__main__")

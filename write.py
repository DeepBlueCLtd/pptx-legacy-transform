"""Stage 5 wrapper — generate the DITA tree from the signed-off CSV.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"write.py").read())

Reads extract.dedupe.csv from the cwd and (re)builds DITA_OUT from
scratch (--clean). Common static pages come from .\\static (the
generator's cwd-relative default). --stub-wav stock.wav swaps every
.wav asset for the committed silent stub to slim the tree for
cross-system transit — drop the flag for a full-audio build. Publish to
a mapped drive, not a \\\\server\\share UNC path. Target-specific paths
and toggles live only in the Config block below.
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
WRITE    = SCRIPTS / "generate_dita.py"
DITA_OUT = Path(r"Z:\dita")
# ----------------------------------------------------------------

sys.argv = [
    str(WRITE),
    "--csv", "extract.dedupe.csv",
    "--out", str(DITA_OUT),
    "--clean",
    "--image-root", str(SOURCE),
    "--stub-wav", "stock.wav",
    # Temporary debugging aid: stamp each gram page with a visible
    # instructor-only block mapping its published week-N/gram-NN back to the
    # source publication, source deck title and original gram number (plus the
    # analysis image's source path). Handy when a published page — e.g. a
    # missing analysis image — needs tracing to the PPTX it came from. Remove
    # this line once the debugging phase is over and the block disappears:
    # "--debug-provenance",
]
runpy.run_path(str(WRITE), run_name="__main__")

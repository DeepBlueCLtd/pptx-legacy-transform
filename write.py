"""Stage 5 wrapper — generate the DITA tree from the signed-off CSV.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"write.py").read())

Reads extract.dedupe.csv from the cwd and (re)builds DITA_OUT from
scratch. Set CLEAN = False in the Config block to keep the existing
DITA_OUT instead, so a suite of documents can be accumulated across
runs and published one by one. Common static pages come from .\\static (the
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
            "snapshot_analysis_docs", "ingest_gram_images", "mock_pptx"):
    sys.modules.pop(mod, None)

# ---- Config ----------------------------------------------------
WRITE    = SCRIPTS / "generate_dita.py"
DITA_OUT = Path(r"Z:\dita")

# True  -> wipe DITA_OUT and rebuild it from scratch (the safe default:
#          this run's output is all that's there).
# False -> keep DITA_OUT and write this run's publication folder(s) into
#          it, so a suite of documents can be built up over successive
#          runs and published one by one. Nothing is removed, so a run
#          that lands in a publication folder an earlier run already
#          built overwrites that map and leaves the earlier gram folders
#          behind as orphans — accumulate distinct publications, and
#          switch back to True whenever a publication is rebuilt.
CLEAN    = True
# ----------------------------------------------------------------

sys.argv = [
    str(WRITE),
    "--csv", "extract.dedupe.csv",
    "--out", str(DITA_OUT),
    "--clean" if CLEAN else "--no-clean",
    "--image-root", str(SOURCE),
    "--stub-wav", "stock.wav",
    # The source-provenance debug block is ON by default for now: each gram page
    # carries a visible instructor-only block mapping its published week-N/gram-NN
    # back to the source publication, source deck title and original gram number
    # (plus the analysis image's source path) — so a published page (e.g. a
    # missing analysis image) can be traced to the PPTX it came from. To turn it
    # off once the debugging phase is over, uncomment the line below:
    # "--no-debug-provenance",
]
runpy.run_path(str(WRITE), run_name="__main__")

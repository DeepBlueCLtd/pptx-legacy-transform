"""Prep-time wrapper — relink .wav-backed GLCs to author-supplied images.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"relink.py").read())

After copying the replacement images (named "Image <N>-...") into each
gram folder under source\\, this walks the tree and rewrites every .glc
that still points at a .wav so it references the matching image instead,
moving the old .wav aside to <name>.wav.bak. Already-converted GLCs are
skipped, so it is safe to re-run as you work through the corpus. Verify
each batch of transitions with `git diff` (the sources are versioned).
Logs to relink.log in the cwd. Add "--dry-run" to sys.argv to preview
without changing anything. Target-specific paths live only in the Config
block below.
"""
import os, sys, runpy
from pathlib import Path

ROOT    = Path(r"C:\dev\AAAC")
PYLIB   = ROOT / "scripts" / "pylib"
SCRIPTS = ROOT / "scripts"
SOURCE  = ROOT / "source"

def cls():
    os.system("cls")

for p in (PYLIB, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

for mod in ("extract_to_csv", "introspect_pptx", "deduplicate_csv",
            "generate_dita", "publish_html", "rehydrate_dita",
            "snapshot_analysis_docs", "relink_glc_to_image", "ingest_gram_images", "mock_pptx"):
    sys.modules.pop(mod, None)

# ---- Config ----------------------------------------------------
RELINK = SCRIPTS / "relink_glc_to_image.py"
# ----------------------------------------------------------------

sys.argv = [
    str(RELINK),
    "--root", str(SOURCE),
    # "--dry-run",
]
runpy.run_path(str(RELINK), run_name="__main__")

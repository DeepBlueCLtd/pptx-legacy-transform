"""Prep-time wrapper — import author gram images and relink wav-backed GLCs.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"ingest.py").read())

The author delivers a parallel tree of analysis-tool screenshots named
"<duration> <wav-stem>.<jpg|jpeg|png>" (e.g. "5m26s WAV 1.jpg"). This
walks that tree against source\\ and, by default, writes a read-only
verify report (ingest_report.txt) of every folder/stem/duration
mismatch with nearest-candidate suggestions — fix the names in the
INCOMING tree by hand, then re-run until it is clean. Once clean, set
APPLY = True in the Config block below (or uncomment "--apply") and
re-run: each matched image is copied beside its .glc under the wav's
stem, the .glc is repointed at it, and the duration is written into
<bottom_crop> so a later extract.py reads it as time_end.

Unlike relink.py, this LEAVES THE .wav IN PLACE (a future user may want
the audio); the generator only copies what the .glc references, so the
wav never reaches dita\\. Verify each batch with `git diff` (the
sources are versioned). Logs to ingest.log in the cwd. Target-specific
paths and the APPLY toggle live only in the Config block below.
"""
import os, sys, runpy
from pathlib import Path

ROOT     = Path(r"C:\dev\AAAC")
PYLIB    = ROOT / "scripts" / "pylib"
SCRIPTS  = ROOT / "scripts"
SOURCE   = ROOT / "source"

def cls():
    os.system("cls")

for p in (PYLIB, SCRIPTS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

for mod in ("extract_to_csv", "introspect_pptx", "deduplicate_csv",
            "generate_dita", "publish_html", "rehydrate_dita",
            "snapshot_analysis_docs", "relink_glc_to_image",
            "ingest_gram_images", "mock_pptx"):
    sys.modules.pop(mod, None)

# ---- Config ----------------------------------------------------
INGEST   = SCRIPTS / "ingest_gram_images.py"
# The author's delivery tree (parallel to source\, without the per-doc
# container folder). Tune to wherever the incoming grams were dropped:
INCOMING = ROOT / "incoming"
# Flip to True only once the verify report is clean, to perform the
# conversion; keep False to re-run the read-only verify/report pass.
APPLY    = False
# ----------------------------------------------------------------

sys.argv = [
    str(INGEST),
    "--incoming-root", str(INCOMING),
    "--source-root", str(SOURCE),
]
if APPLY:
    sys.argv.append("--apply")
runpy.run_path(str(INGEST), run_name="__main__")

"""Rebuild demo/oxygen-sample/dita/ from the committed sample.csv.

    python demo/oxygen-sample/regenerate.py

A **dev-host** runner, not one of the air-gapped target wrappers at the repo
root: it lives under demo/ so it never reaches the release zip, and it derives
its paths from __file__ rather than a per-machine Config block. The committed
DITA tree it writes is the small publication we hand to Oxygen's Responsive
WebHelp template — see README.md beside this file.

Every path is pinned absolutely. --static-root and --seven-questions default to
*cwd-relative* in generate_dita.py, and a missing 7-questions PNG only warns and
dangles its href, so a run from the wrong directory would otherwise commit a
quietly broken snapshot.
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "demo" / "oxygen-sample"
WRITE = ROOT / "scripts" / "generate_dita.py"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
sys.modules.pop("generate_dita", None)

# No --stub-wav: the corpus .wav files are smaller than stock.wav, so the flag
# would make the committed tree both larger and less faithful.
sys.argv = [
    str(WRITE),
    "--csv", str(SAMPLE / "sample.csv"),
    "--out", str(SAMPLE / "dita"),
    "--image-root", str(ROOT),
    "--static-root", str(ROOT / "static"),
    "--seven-questions", str(ROOT / "7_questions.png"),
]
runpy.run_path(str(WRITE), run_name="__main__")

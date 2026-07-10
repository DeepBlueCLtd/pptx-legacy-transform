"""Whole-pipeline orchestrator — run extract -> dedupe -> write -> publish
in sequence, stopping at the first stage that fails.

Run from the WinPython REPL after the once-per-session, by-hand chdir:

    >>> import os; os.chdir(r"C:\\dev\\AAAC")
    >>> exec(open(r"pipeline.py").read())

This is the orchestrating sibling of the single-stage wrappers
(extract.py, dedupe.py, write.py, publish.py): instead of driving one
canonical script, it drives all four in order and **fails fast** — if any
stage returns a non-zero exit code, the run stops there and the later
stages are skipped. Set ONLY in the Config block to scope the whole run
to one source folder (a single document); the scoped extract.csv carries
that scope through the later stages.

Why it differs from the single-stage wrappers: those
``runpy.run_path(..., run_name="__main__")`` and discard the result,
because in the REPL a stage's failure is meant to be silent-and-logged
(it must not kill the interpreter). An orchestrator instead needs the
exit code to decide whether to continue, so it runs each canonical script
under a non-``__main__`` name (keeping the script's own ``sys.exit`` guard
dormant) and calls its ``main()`` directly to capture the return code.

Target-specific paths and toggles live only in the Config block below —
keep DITA_OUT / DITA_OT / STAGING_FOLDER / HTML_OUT in step with write.py
and publish.py. The canonical scripts under scripts\\ are never edited
per-target. Publish to a mapped drive, not a \\\\server\\share UNC path.
"""
from __future__ import annotations

import logging
import runpy
import sys
from pathlib import Path

# ---- Common preamble (paths) -----------------------------------
ROOT    = Path(r"C:\dev\AAAC")
PYLIB   = ROOT / "scripts" / "pylib"
SCRIPTS = ROOT / "scripts"
SOURCE  = ROOT / "source"

# The canonical stage scripts under scripts\ (never edited per-target).
EXTRACT = SCRIPTS / "extract_to_csv.py"
DEDUPE  = SCRIPTS / "deduplicate_csv.py"
WRITE   = SCRIPTS / "generate_dita.py"
PUBLISH = SCRIPTS / "publish_html.py"

# ---- Config ----------------------------------------------------
# Scope the whole run to ONE source folder (the first path segment under
# source\, i.e. a single document), or None to process the entire corpus.
# Mirrors extract_to_csv.py --only: extract writes a scoped extract.csv
# that dedupe/write/publish carry through, so only that document is
# rebuilt. Note write runs with --clean, so a scoped run rebuilds dita\
# to contain only that document.
ONLY = "Instructor Week 1 Grams"

# Output locations — keep these in step with write.py and publish.py.
DITA_OUT       = Path(r"Z:\dita")
DITA_OT        = Path(r"Z:\dita-ot-4.4")
STAGING_FOLDER = Path(r"Z:\dita-build")
HTML_OUT       = Path(r"Z:\html")

# Stages to run, in order. Trim this (e.g. drop "publish" to skip the slow
# DITA-OT render) to stop early; the run still fails fast on any included
# stage.
STAGES = ("extract", "dedupe", "write", "publish")
# ----------------------------------------------------------------

# Canonical modules evicted before a run so a re-exec in the same REPL
# session picks up edited canonical scripts (mirrors the wrappers).
_CANONICAL_MODULES = ("extract_to_csv", "introspect_pptx", "deduplicate_csv",
                      "generate_dita", "publish_html", "rehydrate_dita",
                      "snapshot_analysis_docs", "ingest_gram_images", "mock_pptx")

# The DEBUG log each canonical main() writes in the cwd, named in the
# failure banner so the operator knows where to look.
_STAGE_LOGS = {"extract": "extract.log", "dedupe": "dedup.log",
               "write": "generate.log", "publish": "(console only)"}


def build_stages(only=ONLY, stages=STAGES):
    """Return the ordered ``[(label, script_path, argv), ...]`` to run.

    ``only`` scopes the *extract* stage via ``extract_to_csv --only``; the
    scoped CSV carries through, so no later stage needs the flag. Each
    ``argv`` is a bare option list (no program name) — the canonical
    ``main()`` parses it with argparse.
    """
    extract_argv = ["--input-root", str(SOURCE), "--out", str(ROOT / "extract.csv")]
    if only:
        extract_argv += ["--only", only]
    table = {
        "extract": (EXTRACT, extract_argv),
        "dedupe":  (DEDUPE,  ["--csv", "extract.csv",
                              "--image-root", str(SOURCE),
                              "--out", "extract.dedupe.csv"]),
        "write":   (WRITE,   ["--csv", "extract.dedupe.csv",
                              "--out", str(DITA_OUT), "--clean",
                              "--image-root", str(SOURCE),
                              "--stub-wav", "stock.wav"]),
        "publish": (PUBLISH, ["--dita", str(DITA_OUT), "--out", str(HTML_OUT),
                              "--dita-ot", str(DITA_OT),
                              "--staged", str(STAGING_FOLDER)]),
    }
    return [(label, table[label][0], table[label][1]) for label in stages]


def _reset_root_logging():
    """Drop the previous stage's root-logger handlers so the next stage
    configures logging from a clean slate. Each canonical ``main()``
    rebuilds its own handlers; clearing here also keeps publish_html's
    ``logging.basicConfig`` from silently no-opping onto the prior stage's
    file handler (which would misfile publish output into generate.log)."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)


def run_stage(label, script_path, argv):
    """Load the canonical stage script fresh from disk and call its
    ``main(argv)``, returning the int exit code.

    Runs the script under a non-``__main__`` name so its own ``sys.exit``
    guard stays dormant, then calls ``main()`` directly to capture the
    return code the fail-fast loop needs."""
    _reset_root_logging()
    namespace = runpy.run_path(str(script_path), run_name="__pipeline_stage__")
    return namespace["main"](list(argv))


def run_pipeline(stages, runner=run_stage):
    """Run ``stages`` in order, stopping at the first non-zero exit code.

    Returns 0 when every stage succeeded, otherwise the failing stage's
    exit code. On failure the remaining stages are **skipped** — the
    fail-fast contract."""
    for label, script_path, argv in stages:
        print("\n=== pipeline: %s (%s) ===" % (label, Path(script_path).name))
        rc = runner(label, script_path, argv)
        if rc:
            print("\n*** pipeline FAILED at '%s' (exit %d). Skipping the "
                  "remaining stage(s); see %s in the cwd. ***"
                  % (label, rc, _STAGE_LOGS.get(label, "the stage log")))
            return rc
    print("\n=== pipeline complete: %s ===" % ", ".join(s[0] for s in stages))
    return 0


def _prepare_environment():
    """Put scripts\\pylib (python-pptx) and scripts\\ (sibling imports) on
    sys.path and evict any stale canonical modules, mirroring the
    single-stage wrappers' preamble. Kept out of import time so the module
    stays import-safe for the test suite."""
    for path in (PYLIB, SCRIPTS):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    for module in _CANONICAL_MODULES:
        sys.modules.pop(module, None)


if __name__ == "__main__":
    _prepare_environment()
    _rc = run_pipeline(build_stages(ONLY, STAGES))
    # REPL-safe exit, exactly as the canonical scripts do: surface a
    # non-zero code to a CLI / automation caller so the failure is not
    # swallowed, but never sys.exit when driven interactively via exec()
    # — that would kill the WinPython REPL. sys.ps1 exists only in an
    # interactive session.
    if _rc and not hasattr(sys, "ps1"):
        sys.exit(_rc)

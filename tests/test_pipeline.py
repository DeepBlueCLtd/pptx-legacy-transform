"""Tests for the whole-pipeline orchestrator (pipeline.py at the repo root).

pipeline.py is the orchestrating sibling of the single-stage REPL
wrappers: it drives extract -> dedupe -> write -> publish in order and
fails fast. Unlike the wrappers, its execution is guarded behind
``if __name__ == "__main__":`` (which still fires under REPL ``exec()``,
where ``__name__`` is ``"__main__"``), so importing it here is
side-effect-free and the sequencing / fail-fast logic can be exercised
directly with a fake stage runner — the hardcoded C:\\ Config paths never
need to resolve.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pipeline  # noqa: E402  (after sys.path setup)

# The canonical scripts the four stages must drive.
STAGE_SCRIPTS = {
    "extract": "extract_to_csv.py",
    "dedupe": "deduplicate_csv.py",
    "write": "generate_dita.py",
    "publish": "publish_html.py",
}
ALLOWED_IMPORTS = {"__future__", "logging", "runpy", "sys", "pathlib"}


def _recording_runner(rc_by_label=None):
    """A fake stage runner: records the labels it is asked to run, in
    order, and returns the scripted exit code for each (default 0)."""
    rc_by_label = rc_by_label or {}
    calls: list[str] = []

    def runner(label, script_path, argv):
        calls.append(label)
        return rc_by_label.get(label, 0)

    return runner, calls


class RunPipelineSequencingTests(unittest.TestCase):
    """The fail-fast contract — the heart of the feature."""

    def _stages(self, labels=("extract", "dedupe", "write", "publish")):
        # (label, script_path, argv) triples; the fake runner ignores the
        # path/argv, so dummy values are fine here.
        return [(label, Path(label + ".py"), []) for label in labels]

    def test_runs_every_stage_in_order_when_all_pass(self):
        runner, calls = _recording_runner()
        rc = pipeline.run_pipeline(self._stages(), runner=runner)
        self.assertEqual(rc, 0)
        self.assertEqual(calls, ["extract", "dedupe", "write", "publish"])

    def test_stops_at_first_failure_and_skips_later_stages(self):
        # 'write' fails -> 'publish' must never run, and its rc propagates.
        runner, calls = _recording_runner({"write": 1})
        rc = pipeline.run_pipeline(self._stages(), runner=runner)
        self.assertEqual(rc, 1, "the failing stage's exit code must propagate")
        self.assertEqual(calls, ["extract", "dedupe", "write"],
                         "stages after the failure must be skipped")

    def test_propagates_the_exact_nonzero_code(self):
        runner, calls = _recording_runner({"extract": 2})
        rc = pipeline.run_pipeline(self._stages(), runner=runner)
        self.assertEqual(rc, 2)
        self.assertEqual(calls, ["extract"])

    def test_first_stage_failure_runs_nothing_else(self):
        runner, calls = _recording_runner({"extract": 1})
        pipeline.run_pipeline(self._stages(), runner=runner)
        self.assertEqual(calls, ["extract"])


class BuildStagesTests(unittest.TestCase):
    """Stage wiring: which scripts, in what order, with what scope."""

    def test_default_order_is_extract_dedupe_write_publish(self):
        stages = pipeline.build_stages(only=None,
                                       stages=("extract", "dedupe", "write", "publish"))
        self.assertEqual([label for label, _, _ in stages],
                         ["extract", "dedupe", "write", "publish"])

    def test_each_stage_targets_its_canonical_script(self):
        stages = pipeline.build_stages(only=None)
        for label, script_path, _ in stages:
            self.assertEqual(Path(script_path).name, STAGE_SCRIPTS[label])
            # The named canonical script must actually exist in the repo.
            self.assertTrue((REPO_ROOT / "scripts" / STAGE_SCRIPTS[label]).is_file(),
                            f"missing scripts/{STAGE_SCRIPTS[label]}")

    def test_only_scopes_the_extract_stage_alone(self):
        stages = pipeline.build_stages(only="Instructor Week 1 Grams")
        by_label = {label: argv for label, _, argv in stages}
        self.assertIn("--only", by_label["extract"])
        idx = by_label["extract"].index("--only")
        self.assertEqual(by_label["extract"][idx + 1], "Instructor Week 1 Grams")
        for other in ("dedupe", "write", "publish"):
            self.assertNotIn("--only", by_label[other],
                             f"{other} must not receive --only; the scoped CSV "
                             "already carries the scope")

    def test_only_none_omits_the_flag(self):
        stages = pipeline.build_stages(only=None)
        extract_argv = next(argv for label, _, argv in stages if label == "extract")
        self.assertNotIn("--only", extract_argv)

    def test_stages_selection_is_honoured(self):
        # Trimming STAGES (e.g. to skip the slow publish) is supported.
        stages = pipeline.build_stages(only=None, stages=("extract", "dedupe", "write"))
        self.assertEqual([label for label, _, _ in stages],
                         ["extract", "dedupe", "write"])

    def test_argv_lists_carry_no_program_name(self):
        # main() parses argv with argparse, which does NOT skip element 0;
        # every list must start with an option flag, not a script path.
        stages = pipeline.build_stages(only="X")
        for label, _, argv in stages:
            self.assertTrue(argv and argv[0].startswith("--"),
                            f"{label} argv must begin with an option flag")


class OrchestratorHygieneTests(unittest.TestCase):
    """Air-gapped shape checks, mirroring tests/test_wrappers.py."""

    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse((REPO_ROOT / "pipeline.py").read_text(encoding="utf-8"))

    def _imported_top_modules(self):
        names = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    names.add(node.module.split(".", 1)[0])
        return names

    def test_imports_only_the_stdlib(self):
        self.assertLessEqual(
            self._imported_top_modules(), ALLOWED_IMPORTS,
            "pipeline.py must stay stdlib-only (canonical scripts are loaded "
            "by path at runtime, not imported)")

    def test_never_chdir(self):
        # The operator chdirs once, by hand; the orchestrator must not.
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                func = node.func
                if (isinstance(func, ast.Attribute)
                        and isinstance(func.value, ast.Name)
                        and func.value.id == "os" and func.attr == "chdir"):
                    self.fail("pipeline.py must not chdir")

    def test_execution_is_guarded_for_import_safety(self):
        # The live run must sit behind `if __name__ == "__main__":` so the
        # module imports without executing the pipeline.
        guards = [
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        ]
        self.assertTrue(guards, "pipeline.py must guard execution behind "
                                "`if __name__ == '__main__':`")

    def test_has_repl_safe_exit_guard(self):
        # Mirrors the canonical scripts: only sys.exit when not interactive.
        source = (REPO_ROOT / "pipeline.py").read_text(encoding="utf-8")
        self.assertIn('hasattr(sys, "ps1")', source,
                      "pipeline.py must gate sys.exit on a non-interactive "
                      "session so exec() in the REPL never kills it")


if __name__ == "__main__":
    unittest.main()

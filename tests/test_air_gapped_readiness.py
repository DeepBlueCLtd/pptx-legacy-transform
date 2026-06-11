"""Air-gapped readiness checks (User Story 5).

These tests assert structural properties of the project that the
air-gapped maintainer relies on: only ``pptx`` as a third-party import,
the test suite runs end-to-end in under one minute, and every script
has a paired test module.
"""

from __future__ import annotations

import ast
import os
import sys
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Import names that ship with the standard library on Python 3.11+.
# Conservative, easy to extend; failures here fail loud, which is the
# point of FR-017.
STDLIB_NAMES: set[str] = set(sys.stdlib_module_names) | {
    "__future__",
}

ALLOWED_THIRD_PARTY: set[str] = {"pptx", "lxml"}

# Deliberate, contained prep-time imports permitted in a single script only
# (never on the pipeline runtime path, never in the test suite at import
# time). ``snapshot_analysis_docs.py`` imports Pillow defensively for the
# optional margin-trim/DPI step (feature 007 FR-017), behind a graceful
# full-page fallback when absent. See specs/007 plan Constitution Check.
PREP_TIME_ALLOWED: dict[str, set[str]] = {
    "snapshot_analysis_docs.py": {"PIL"},
}


SCRIPTS = (
    "mock_pptx.py",
    "introspect_pptx.py",
    "extract_to_csv.py",
    "generate_dita.py",
    "publish_html.py",
    "deduplicate_csv.py",
    "rehydrate_dita.py",
    "snapshot_analysis_docs.py",
)

# Thin REPL wrappers at the repo root (README "Running on the air-gapped
# target machine"). Scanned for the stdlib-only guarantee like the
# canonical scripts; tests/test_wrappers.py covers their shape.
WRAPPERS = (
    "extract.py",
    "dedupe.py",
    "write.py",
    "publish.py",
    "introspect.py",
    "snapshot.py",
)


def _iter_test_cases(suite: unittest.TestSuite):
    """Recursively yield every TestCase under ``suite``."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_test_cases(item)
        else:
            yield item


def _imported_top_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                names.add(node.module.split(".", 1)[0])
    return names


class AirGappedReadinessTests(unittest.TestCase):

    def test_no_third_party_imports_other_than_pptx(self) -> None:
        targets = [REPO_ROOT / "scripts" / s for s in SCRIPTS]
        targets.extend(REPO_ROOT / w for w in WRAPPERS)
        targets.extend((REPO_ROOT / "tests").glob("test_*.py"))
        targets.append(REPO_ROOT / "tests" / "conftest_helpers.py")
        offenders: list[tuple[str, str]] = []
        for path in targets:
            for mod in _imported_top_modules(path):
                if mod in STDLIB_NAMES:
                    continue
                if mod in ALLOWED_THIRD_PARTY:
                    continue
                if mod in PREP_TIME_ALLOWED.get(path.name, set()):
                    continue
                # In-tree modules: scripts at root and the test package.
                in_tree_scripts = {Path(s).stem for s in SCRIPTS}
                if mod in in_tree_scripts | {"tests"}:
                    continue
                offenders.append((path.name, mod))
        self.assertEqual(offenders, [], f"unexpected third-party imports: {offenders}")

    def test_test_suite_runs_under_one_minute(self) -> None:
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=str(REPO_ROOT / "tests"), pattern="test_*.py")
        filtered = unittest.TestSuite()
        for case in _iter_test_cases(suite):
            if case.id().split(".")[0] != "test_air_gapped_readiness":
                filtered.addTest(case)
        with open(os.devnull, "w") as devnull:
            runner = unittest.TextTestRunner(verbosity=0, stream=devnull)
            start = time.perf_counter()
            runner.run(filtered)
            elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 60.0, f"suite took {elapsed:.2f}s; budget is 60s")

    def test_every_script_has_corresponding_test_module(self) -> None:
        for script in SCRIPTS:
            base = Path(script).stem
            test_module = REPO_ROOT / "tests" / f"test_{base}.py"
            self.assertTrue(test_module.is_file(),
                            f"no test module for {script} (expected {test_module.name})")
        # The wrappers are covered collectively rather than one-per-file.
        self.assertTrue((REPO_ROOT / "tests" / "test_wrappers.py").is_file(),
                        "no test module for the root wrapper scripts")


if __name__ == "__main__":
    unittest.main()

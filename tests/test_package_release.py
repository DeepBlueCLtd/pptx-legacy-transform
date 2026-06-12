"""Packaging contract for the GitHub-release deliverable zip.

Guards the air-gap transfer artifact built by
.github/scripts/package_release.py: the archive mirrors the target layout
(root scripts under scripts/, static/ and the loose operator files at the
root), carries nothing dev-host-only, and is byte-identical when rebuilt.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGER = REPO_ROOT / ".github" / "scripts" / "package_release.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("package_release", PACKAGER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(PACKAGER.is_file(), "packaging script not present in this tree")
class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_packager()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def _build(self, name):
        out = self.tmp / name
        self.module.build_zip(out, timestamp=1700000000)
        return out

    def test_archive_mirrors_target_layout(self):
        with zipfile.ZipFile(self._build("layout.zip")) as archive:
            names = set(archive.namelist())
        for canonical in (
            "deduplicate_csv.py",
            "extract_to_csv.py",
            "generate_dita.py",
            "introspect_pptx.py",
            "publish_html.py",
        ):
            self.assertIn("scripts/" + canonical, names)
        self.assertIn("static/welcome.dita", names)
        self.assertIn("static/security.dita", names)
        self.assertIn("stock.wav", names)
        self.assertIn("requirements.txt", names)
        self.assertIn("README.md", names)
        # The wrapper templates (and the pipeline.py orchestrator) ship under
        # wrappers/, so an extract-over-ROOT\ upgrade delivers a new wrapper
        # without clobbering the operator's tuned root-level copies.
        for wrapper in ("extract.py", "dedupe.py", "write.py", "publish.py",
                        "introspect.py", "snapshot.py", "pipeline.py"):
            self.assertIn("wrappers/" + wrapper, names)

    def test_archive_carries_only_deliverables(self):
        with zipfile.ZipFile(self._build("only.zip")) as archive:
            names = archive.namelist()
        for name in names:
            allowed = (
                name.startswith("scripts/")
                or name.startswith("static/")
                or name.startswith("wrappers/")
                or name in self.module.ROOT_FILES
            )
            self.assertTrue(allowed, f"unexpected archive entry: {name}")
        self.assertNotIn("run_pipeline.bat", names)
        # Dev-only mock tooling stays out of the deliverable.
        self.assertNotIn("scripts/generate_mock_analysis_sheet.py", names)
        # The wrappers ship under wrappers/, never at the archive root, so an
        # extract-over-ROOT\ upgrade can't overwrite the operator's tuned copies.
        for wrapper in ("extract.py", "dedupe.py", "write.py",
                        "publish.py", "introspect.py", "snapshot.py",
                        "pipeline.py"):
            self.assertNotIn(wrapper, names)
            self.assertNotIn("scripts/" + wrapper, names)
        # vendor assets sit beside publish_html.py in the repo but are
        # not part of the archive contract.
        self.assertFalse(any(n.startswith("scripts/vendor/") for n in names),
                         "vendor assets must not ship in the archive")

    def test_rebuild_is_byte_identical(self):
        first = self._build("first.zip")
        second = self._build("second.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()

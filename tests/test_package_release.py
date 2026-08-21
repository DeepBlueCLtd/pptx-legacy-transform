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
        # The Oxygen GramFrame overlay travels under theme/ so the production
        # publisher on the air-gapped box can render interactive grams.
        self.assertIn(
            "theme/gramframe-oxygen/resources/gramframe.bundle.js", names)
        self.assertIn(
            "theme/gramframe-oxygen/page-templates-fragments/libraries/gramframe.xml",
            names)
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
                or name.startswith("theme/")
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

    def test_theme_bundle_matches_vendored_bundle(self):
        # Every GramFrame bundle in the tree must stay byte-identical to the one
        # publish_html.py vendors, so the production publish and the dev preview
        # render grams the same way. Three copies exist: the vendored original,
        # the standalone overlay (install instructions for a foreign template),
        # and the ready-to-publish pptx-transform template.
        vendored = REPO_ROOT / "scripts" / "vendor" / "gramframe" / "gramframe.bundle.js"
        self.assertTrue(vendored.is_file(), "vendored GramFrame bundle missing")
        expected = vendored.read_bytes()
        for label, copy in (
            ("theme/gramframe-oxygen",
             REPO_ROOT / "theme" / "gramframe-oxygen" / "resources"
             / "gramframe.bundle.js"),
            ("theme/pptx-transform",
             REPO_ROOT / "theme" / "pptx-transform" / "resources"
             / "gramframe.bundle.js"),
        ):
            with self.subTest(copy=label):
                self.assertTrue(copy.is_file(),
                                f"{label} GramFrame bundle missing")
                self.assertEqual(
                    expected, copy.read_bytes(),
                    f"{label} GramFrame bundle has drifted from "
                    "scripts/vendor/gramframe/; update every copy (and their "
                    "VERSION files) together")

    def test_publishing_template_wires_the_overlays(self):
        # pptx-transform is the template the operator actually publishes with,
        # so it must carry both overlays wired in — not just the payload files.
        # A fragment under a bare <fragments>, or directly under <webhelp>,
        # fails the Oxygen publish with "Build failed with an exception: null".
        import xml.etree.ElementTree as ET

        opt = (REPO_ROOT / "theme" / "pptx-transform" / "pptx-transform.opt")
        self.assertTrue(opt.is_file(), "pptx-transform.opt missing")
        webhelp = ET.parse(opt).getroot().find("webhelp")

        # Stock default is "no", which leaves each week_N.dita page an empty
        # <h1> and its grams reachable only from the side TOC.
        params = {p.get("name"): p.get("value")
                  for p in webhelp.findall("parameters/parameter")}
        self.assertEqual(params.get("webhelp.show.child.links"), "yes")

        css = [c.get("file") for c in webhelp.findall("resources/css")]
        self.assertIn("resources/hide-search.css", css)
        self.assertEqual(css[-1], "resources/hide-search.css",
                         "hide-search.css must load last to win the cascade")

        fragments = webhelp.findall("html-fragments/fragment")
        self.assertEqual(
            [(f.get("file"), f.get("placeholder")) for f in fragments],
            [("page-templates-fragments/libraries/gramframe.xml",
              "webhelp.fragment.head.topic.page")])

        # Oxygen's schematron asserts every referenced file resolves on disk.
        for el in webhelp.iter():
            ref = el.get("file")
            if ref:
                self.assertTrue((opt.parent / ref).is_file(),
                                f"{el.tag} references missing file: {ref}")

    def test_rebuild_is_byte_identical(self):
        first = self._build("first.zip")
        second = self._build("second.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()

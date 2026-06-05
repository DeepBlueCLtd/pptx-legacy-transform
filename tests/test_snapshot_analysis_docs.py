"""Tests for snapshot_analysis_docs.py (Feature 007).

The renderer is stubbed via ``--renderer-cmd`` pointing at
``tests/fixtures/fake_renderer.py`` (research R6), so the suite stays
stdlib-only and LibreOffice-free. The ``.doc``/``.docx`` inputs are
placeholder bytes -- the snapshotter never parses them, it only hands them
to the renderer.
"""

from __future__ import annotations

import importlib
import os
import shlex
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import snapshot_analysis_docs as nas  # noqa: E402

FAKE_RENDERER = REPO_ROOT / "tests" / "fixtures" / "fake_renderer.py"
TMP = REPO_ROOT / "tests" / "_tmp" / "snapshot"

# A renderer command the snapshotter can shlex-split back into argv. Quoting
# keeps spaces in the interpreter path (e.g. on Windows) intact.
STUB_CMD = f"{shlex.quote(sys.executable)} {shlex.quote(str(FAKE_RENDERER))}"


def _pil_available() -> bool:
    try:
        importlib.import_module("PIL")
        return True
    except ImportError:
        return False


class SnapshotTestBase(unittest.TestCase):

    def setUp(self) -> None:
        self.root = TMP / self._testMethodName
        if self.root.exists():
            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def _write_doc(self, name: str, content: bytes = b"placeholder doc bytes") -> Path:
        path = self.root / name
        path.write_bytes(content)
        return path

    def _run(self, *, renderer_cmd: str = STUB_CMD, dry_run: bool = False) -> int:
        argv = ["--content-root", str(self.root), "--renderer-cmd", renderer_cmd]
        if dry_run:
            argv.append("--dry-run")
        return nas.main(argv)


# -----------------------------------------------------------------------------
# Phase 3: US1 & US2 -- doc/docx -> inline image
# -----------------------------------------------------------------------------

class RenderHappyPathTests(SnapshotTestBase):

    def test_doc_only_folder_produces_png(self) -> None:  # T005 (US1)
        doc = self._write_doc("aaa_analysis.doc")
        rc = self._run()
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "a .doc analysis sheet must gain a sibling .png")

    def test_docx_only_folder_produces_png(self) -> None:  # T006 (US2)
        doc = self._write_doc("bbb_analysis.docx")
        rc = self._run()
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "a .docx analysis sheet must gain a sibling .png")

    def test_png_already_present_is_noop(self) -> None:  # T007 (US1)
        doc = self._write_doc("ccc_analysis.doc")
        png = doc.with_suffix(".png")
        png.write_bytes(b"existing png")
        before = png.stat().st_mtime_ns
        results = nas.snapshot(self.root, STUB_CMD, dry_run=False)
        word_results = [r for r in results if r.source_path == doc]
        self.assertEqual(len(word_results), 1)
        self.assertEqual(word_results[0].outcome, "skipped_has_png")
        self.assertEqual(png.read_bytes(), b"existing png", "PNG must not be re-rendered")
        self.assertEqual(png.stat().st_mtime_ns, before, "PNG mtime must be preserved")

    def test_non_analysis_word_doc_not_rendered(self) -> None:  # T008 (US2 / FR-015)
        self._write_doc("source_data.doc")
        analysis = self._write_doc("ddd_analysis.doc")
        rc = self._run()
        self.assertEqual(rc, 0)
        self.assertTrue(analysis.with_suffix(".png").exists())
        self.assertFalse((self.root / "source_data.png").exists(),
                         "unrelated Word docs must not be rendered (FR-015 guard)")

    def test_dry_run_writes_nothing(self) -> None:
        doc = self._write_doc("eee_analysis.doc")
        rc = self._run(dry_run=True)
        self.assertEqual(rc, 0)
        self.assertFalse(doc.with_suffix(".png").exists(),
                         "--dry-run must not write any file")


# -----------------------------------------------------------------------------
# Phase 4: US3 -- failures visible, never fatal
# -----------------------------------------------------------------------------

class FailurePathTests(SnapshotTestBase):

    def test_renderer_failure_is_warning_not_abort(self) -> None:  # T015 (US3)
        doc = self._write_doc("fff_analysis.doc")
        with mock.patch.dict(os.environ, {"FAKE_RENDERER_EXIT": "1"}):
            with self.assertLogs(nas.LOGGER, level="WARNING") as cm:
                results = nas.snapshot(self.root, STUB_CMD, dry_run=False)
                rc = self._run()
        self.assertEqual(rc, 0, "render failure must not abort the run")
        word_results = [r for r in results if r.source_path == doc]
        self.assertEqual(word_results[0].outcome, "render_failed")
        self.assertFalse(doc.with_suffix(".png").exists())
        self.assertTrue(any("render failed" in m for m in cm.output))

    def test_renderer_absent_is_warning_not_abort(self) -> None:
        self._write_doc("ggg_analysis.doc")
        rc = self._run(renderer_cmd="definitely_not_a_real_binary_xyz")
        self.assertEqual(rc, 0, "missing renderer must not abort the run")

    def test_multipage_source_warns_not_truncates(self) -> None:  # T016 (US3)
        doc = self._write_doc("hhh_analysis.doc")
        with mock.patch.dict(os.environ, {"FAKE_RENDERER_PAGES": "2"}):
            with self.assertLogs(nas.LOGGER, level="WARNING") as cm:
                results = nas.snapshot(self.root, STUB_CMD, dry_run=False)
        word_results = [r for r in results if r.source_path == doc]
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "page-1 PNG must still be produced for a multi-page source")
        self.assertTrue(word_results[0].multipage)
        self.assertTrue(any("multi-page" in m for m in cm.output))

    def test_summary_records_failure(self) -> None:
        self._write_doc("iii_analysis.doc")
        with mock.patch.dict(os.environ, {"FAKE_RENDERER_EXIT": "1"}):
            with mock.patch("builtins.print") as printed:
                rc = self._run()
        self.assertEqual(rc, 0)
        summary = "".join(str(c.args[0]) for c in printed.call_args_list if c.args)
        self.assertIn("render_failed=1", summary)


# -----------------------------------------------------------------------------
# Phase 5: tidy (margin-trim + DPI), defensively imported
# -----------------------------------------------------------------------------

class TidyTests(SnapshotTestBase):

    def test_tidy_falls_back_without_pillow(self) -> None:  # T022
        doc = self._write_doc("jjj_analysis.doc")
        # Simulate Pillow absent: block the guarded import inside tidy_image.
        real_import = __import__

        def fake_import(name, *a, **k):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("simulated: no Pillow")
            return real_import(name, *a, **k)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            with self.assertLogs(nas.LOGGER, level="INFO"):
                results = nas.snapshot(self.root, STUB_CMD, dry_run=False)
        word_results = [r for r in results if r.source_path == doc]
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "full-page PNG kept when Pillow is absent")
        self.assertFalse(word_results[0].tidied)

    @unittest.skipUnless(_pil_available(), "Pillow not installed")
    def test_tidy_crops_when_pillow_present(self) -> None:  # T023
        # Import via importlib so the canonical suite stays PIL-free at
        # static-import time (air-gapped readiness check).
        Image = importlib.import_module("PIL.Image")

        doc = self._write_doc("kkk_analysis.doc")
        png = doc.with_suffix(".png")
        # A white canvas with a small black block -> tidy should crop tightly.
        im = Image.new("RGB", (200, 200), (255, 255, 255))
        for x in range(80, 120):
            for y in range(80, 120):
                im.putpixel((x, y), (0, 0, 0))
        im.save(png)
        with Image.open(png) as opened:
            self.assertEqual(opened.size, (200, 200))
        # Re-render is skipped (PNG present), so tidy directly.
        tidied = nas.tidy_image(png)
        self.assertTrue(tidied)
        with Image.open(png) as cropped:
            w, h = cropped.size
        self.assertLess(w, 200, "cropped width should shrink")
        self.assertLess(h, 200, "cropped height should shrink")


# -----------------------------------------------------------------------------
# Phase 6: reverse PNG -> .docx wrap
# -----------------------------------------------------------------------------

class ReverseWrapTests(SnapshotTestBase):

    def test_png_only_sheet_gets_docx_wrapper(self) -> None:  # T026
        import xml.etree.ElementTree as ET
        import zipfile

        png = self.root / "eee_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        results = nas.snapshot(self.root, STUB_CMD, dry_run=False)
        docx = png.with_suffix(".docx")
        self.assertTrue(docx.exists(), "a png-only analysis sheet must gain a .docx")
        wrap_results = [r for r in results if r.source_path == png]
        self.assertTrue(any(r.docx_wrapped for r in wrap_results))
        with zipfile.ZipFile(docx) as zf:
            self.assertEqual(zf.testzip(), None, "zip must be openable")
            ET.fromstring(zf.read("word/document.xml"))  # must parse
            self.assertIn("word/media/image1.png", zf.namelist())

    def test_reverse_wrap_is_idempotent(self) -> None:  # T027
        png = self.root / "fff_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        nas.snapshot(self.root, STUB_CMD, dry_run=False)
        docx = png.with_suffix(".docx")
        first = docx.read_bytes()
        mtime = docx.stat().st_mtime_ns
        nas.snapshot(self.root, STUB_CMD, dry_run=False)
        self.assertEqual(docx.read_bytes(), first, "reverse .docx must be byte-stable")
        self.assertEqual(docx.stat().st_mtime_ns, mtime, "no re-wrap when .docx exists")

    def test_no_reverse_wrap_suppresses_docx_synthesis(self) -> None:
        """``--no-reverse-wrap`` (reverse_wrap=False) must skip FR-018:
        a png-only analysis sheet stays png-only, no synthetic .docx is
        written, and no result records ``docx_wrapped=True``. For
        workflows where the source corpus must not be mutated with
        synthesised Word files."""
        png = self.root / "ggg_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        results = nas.snapshot(
            self.root, STUB_CMD, dry_run=False, reverse_wrap=False,
        )
        docx = png.with_suffix(".docx")
        self.assertFalse(
            docx.exists(),
            "--no-reverse-wrap must not synthesise a .docx for png-only sheets",
        )
        self.assertFalse(
            any(r.docx_wrapped for r in results),
            "no result should be marked docx_wrapped under --no-reverse-wrap",
        )

    def test_cli_no_reverse_wrap_threads_through_main(self) -> None:
        """The ``--no-reverse-wrap`` CLI flag must reach ``snapshot()`` so
        invoking via ``main`` produces the same suppression as the direct
        keyword argument."""
        png = self.root / "hhh_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        rc = nas.main([
            "--content-root", str(self.root),
            "--renderer-cmd", STUB_CMD,
            "--no-reverse-wrap",
        ])
        self.assertEqual(rc, 0)
        self.assertFalse(
            png.with_suffix(".docx").exists(),
            "CLI --no-reverse-wrap must suppress reverse wrap end-to-end",
        )


# -----------------------------------------------------------------------------
# Selection + classification units (Phase 2)
# -----------------------------------------------------------------------------

class SelectionTests(SnapshotTestBase):

    def test_iter_selects_only_analysis_word_docs(self) -> None:
        self._write_doc("aaa_analysis.doc")
        self._write_doc("bbb_ANALYSIS.docx")
        self._write_doc("source_data.doc")
        (self.root / "notes.txt").write_text("x")
        (self.root / "Analysis.png").write_bytes(b"img")
        found = {p.name for p in nas.iter_analysis_sheets(self.root)}
        self.assertEqual(found, {"aaa_analysis.doc", "bbb_ANALYSIS.docx"})

    def test_needs_render_reflects_png_presence(self) -> None:
        doc = self._write_doc("ccc_analysis.doc")
        self.assertTrue(nas.needs_render(doc))
        doc.with_suffix(".png").write_bytes(b"img")
        self.assertFalse(nas.needs_render(doc))


class IdempotencyTests(SnapshotTestBase):

    def test_second_run_writes_nothing(self) -> None:
        doc = self._write_doc("aaa_analysis.doc")
        self._run()
        png = doc.with_suffix(".png")
        self.assertTrue(png.exists())
        mtime = png.stat().st_mtime_ns
        results = nas.snapshot(self.root, STUB_CMD, dry_run=False)
        word_results = [r for r in results if r.source_path == doc]
        self.assertEqual(word_results[0].outcome, "skipped_has_png")
        self.assertEqual(png.stat().st_mtime_ns, mtime)


if __name__ == "__main__":
    unittest.main()

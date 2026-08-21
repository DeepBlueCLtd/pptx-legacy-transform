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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

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

    def _run(
        self, *, renderer_cmd: str = STUB_CMD, dry_run: bool = False,
        extra_names: list[str] | None = None,
    ) -> int:
        argv = ["--content-root", str(self.root), "--renderer-cmd", renderer_cmd]
        if dry_run:
            argv.append("--dry-run")
        for token in extra_names or []:
            argv += ["--extra-name", token]
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
# Feature 013 (US2): the pipeline never creates Word documents
# -----------------------------------------------------------------------------

class NoWordSynthesisTests(SnapshotTestBase):
    """Feature 007's FR-018 reverse wrap is removed, not merely defaulted off."""

    def test_png_only_sheet_gains_no_word_document(self) -> None:
        """The behaviour the removed step existed to provide, asserted absent.

        A png-only analysis sheet had no editable original before the run and
        must still have none after it — an honest absence tells an analyst to
        re-author the sheet, where a picture-only .docx would waste their time.
        """
        png = self.root / "eee_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        nas.snapshot(self.root, STUB_CMD, dry_run=False)
        self.assertFalse(
            png.with_suffix(".docx").exists(),
            "the pipeline must never fabricate a Word document",
        )
        self.assertEqual(
            sorted(p.name for p in self.root.iterdir()), ["eee_analysis.png"],
            "a png-only sheet must leave the folder exactly as it was",
        )

    def test_no_cli_option_reenables_wrapping(self) -> None:
        """FR-010: removed outright, so no flag can arm the trap again."""
        png = self.root / "hhh_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        with self.assertRaises(SystemExit):
            nas.main([
                "--content-root", str(self.root),
                "--renderer-cmd", STUB_CMD,
                "--no-reverse-wrap",
            ])
        self.assertFalse(png.with_suffix(".docx").exists())

    def test_word_to_png_direction_is_untouched(self) -> None:
        """FR-012: removing the wrap must not disturb the rendering path."""
        doc = self._write_doc("iii_analysis.docx")
        rc = self._run()
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "Word -> PNG rendering must still work")


# -----------------------------------------------------------------------------
# Feature 013 (US3): sweeping the wrappers earlier runs already wrote
# -----------------------------------------------------------------------------

def _write_fabricated_wrapper(path: Path) -> Path:
    """Write a byte-exact replica of what the removed wrap step produced.

    The generator is gone, so the fixture has to reconstruct its output: these
    files exist in real source trees as historical artefacts, and the sweep is
    judged on recognising them. Mirrors the five parts and the ``AnalysisSheet``
    drawing name the removed ``wrap_png_in_docx`` wrote.
    """
    import zipfile

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("_rels/.rels", "<Relationships/>")
        zf.writestr("word/_rels/document.xml.rels", "<Relationships/>")
        zf.writestr(
            "word/document.xml",
            '<w:document><wp:docPr id="1" name="AnalysisSheet"/></w:document>')
        zf.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    return path


def _write_genuine_docx(path: Path, *, with_image: bool = True) -> Path:
    """Write a plausible author-written .docx that must survive the sweep.

    Deliberately adversarial: it embeds a full-page image and even carries the
    same drawing name, so the only thing separating it from a fabrication is the
    part list — a real Word document always ships styles/settings/docProps that
    the fabricated one never had.
    """
    import zipfile

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("_rels/.rels", "<Relationships/>")
        zf.writestr("word/_rels/document.xml.rels", "<Relationships/>")
        zf.writestr(
            "word/document.xml",
            '<w:document><wp:docPr id="1" name="AnalysisSheet"/>'
            "<w:p>real editable text</w:p></w:document>")
        zf.writestr("word/styles.xml", "<w:styles/>")
        zf.writestr("word/settings.xml", "<w:settings/>")
        zf.writestr("docProps/core.xml", "<cp:coreProperties/>")
        if with_image:
            zf.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    return path


class WrapperSweepTests(SnapshotTestBase):

    def test_fabricated_wrapper_is_detected(self) -> None:
        wrapper = _write_fabricated_wrapper(self.root / "a_analysis.docx")
        self.assertTrue(nas.is_fabricated_wrapper(wrapper))

    def test_genuine_word_document_is_not_detected(self) -> None:
        """FR-014: the sweep's failure mode must be leaving a file alone."""
        genuine = _write_genuine_docx(self.root / "b_analysis.docx")
        self.assertFalse(
            nas.is_fabricated_wrapper(genuine),
            "an author's document with a full-page image must never match",
        )

    def test_doc_and_unreadable_files_are_not_detected(self) -> None:
        legacy = self.root / "c_analysis.doc"
        legacy.write_bytes(b"\xd0\xcf\x11\xe0 legacy binary doc")
        junk = self.root / "d_analysis.docx"
        junk.write_bytes(b"not a zip at all")
        self.assertFalse(nas.is_fabricated_wrapper(legacy))
        self.assertFalse(nas.is_fabricated_wrapper(junk))

    def test_report_only_is_the_default_and_deletes_nothing(self) -> None:
        """FR-016: deletion is the opt-in, not the default."""
        wrapper = _write_fabricated_wrapper(self.root / "e_analysis.docx")
        found = nas.sweep_wrappers(self.root)
        self.assertEqual(found, [wrapper])
        self.assertTrue(wrapper.exists(), "default mode must not delete")

    def test_apply_deletes_only_the_wrappers(self) -> None:
        wrapper = _write_fabricated_wrapper(self.root / "f_analysis.docx")
        genuine = _write_genuine_docx(self.root / "g_analysis.docx")
        png = self.root / "f_analysis.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        found = nas.sweep_wrappers(self.root, apply_changes=True)
        self.assertEqual(found, [wrapper])
        self.assertFalse(wrapper.exists(), "the fabrication must be deleted")
        self.assertTrue(genuine.exists(), "the author's document must survive")
        self.assertTrue(png.exists(), "unrelated files must be untouched")

    def test_wrapper_beside_genuine_doc_is_swept(self) -> None:
        """FR-015: the legacy .doc deck case the removed step's .docx-only
        existence check created — a fabrication sitting next to the real thing.
        A scan that skipped folders already holding a Word document would miss
        exactly the folders where the fake is most dangerous."""
        legacy = self.root / "Analysis Sheet.doc"
        legacy.write_bytes(b"\xd0\xcf\x11\xe0 genuine legacy sheet")
        wrapper = _write_fabricated_wrapper(self.root / "Analysis Sheet.docx")
        found = nas.sweep_wrappers(self.root, apply_changes=True)
        self.assertEqual(found, [wrapper])
        self.assertFalse(wrapper.exists())
        self.assertTrue(legacy.exists(), "the genuine .doc must survive")

    def test_sweep_is_idempotent(self) -> None:
        """013 FR-018: a swept tree yields nothing and changes nothing."""
        _write_fabricated_wrapper(self.root / "h_analysis.docx")
        genuine = _write_genuine_docx(self.root / "i_analysis.docx")
        before = genuine.read_bytes()
        nas.sweep_wrappers(self.root, apply_changes=True)
        second = nas.sweep_wrappers(self.root, apply_changes=True)
        self.assertEqual(second, [], "a swept tree must report nothing")
        self.assertEqual(genuine.read_bytes(), before)

    def test_sweep_finds_wrappers_recursively_and_sorted(self) -> None:
        nested = self.root / "Week 1" / "Gram 3"
        nested.mkdir(parents=True)
        second = _write_fabricated_wrapper(nested / "Analysis Sheet.docx")
        first = _write_fabricated_wrapper(self.root / "A_analysis.docx")
        self.assertEqual(nas.find_fabricated_wrappers(self.root), sorted([first, second]))

    def test_cli_sweep_reports_then_applies(self) -> None:
        wrapper = _write_fabricated_wrapper(self.root / "j_analysis.docx")
        rc = nas.main(["--content-root", str(self.root), "--sweep-wrappers"])
        self.assertEqual(rc, 0)
        self.assertTrue(wrapper.exists(), "CLI sweep must report before deleting")
        rc = nas.main([
            "--content-root", str(self.root), "--sweep-wrappers", "--apply"])
        self.assertEqual(rc, 0)
        self.assertFalse(wrapper.exists(), "--apply must delete")

    def test_apply_without_sweep_warns_and_renders(self) -> None:
        doc = self._write_doc("k_analysis.docx")
        with self.assertLogs(nas.LOGGER, level="WARNING") as cm:
            rc = nas.main([
                "--content-root", str(self.root),
                "--renderer-cmd", STUB_CMD, "--apply",
            ])
        self.assertEqual(rc, 0)
        self.assertTrue(any("no effect without --sweep-wrappers" in m for m in cm.output))
        self.assertTrue(doc.with_suffix(".png").exists())


# -----------------------------------------------------------------------------
# --extra-name: opt-in for sheets that deviate from the *analysis* convention
# -----------------------------------------------------------------------------

class ExtraNameTests(SnapshotTestBase):

    def test_extra_name_selects_nonconforming_doc(self) -> None:
        doc = self._write_doc("X-aaa.doc")
        self._write_doc("source_data.doc")
        rc = self._run(extra_names=["X-aaa"])
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "an --extra-name sheet must gain a sibling .png")
        self.assertFalse((self.root / "source_data.png").exists(),
                         "unrelated Word docs must stay untouched (FR-015 guard)")

    def test_without_extra_name_nonconforming_doc_is_skipped(self) -> None:
        doc = self._write_doc("X-aaa.doc")
        rc = self._run()
        self.assertEqual(rc, 0)
        self.assertFalse(doc.with_suffix(".png").exists(),
                         "default selection must stay *analysis*-only")

    def test_extra_name_matches_case_insensitively(self) -> None:
        # Real-corpus shape: no 'analysis' token, interior spaces, mixed case.
        doc = self._write_doc("V III .doc")
        rc = self._run(extra_names=["v iii"])
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "extra-name tokens must match case-insensitively")

    def test_iter_selects_extra_names_alongside_convention(self) -> None:
        self._write_doc("X-aaa.doc")
        self._write_doc("normal_analysis.doc")
        self._write_doc("source_data.doc")
        found = {p.name for p in nas.iter_analysis_sheets(self.root, ("x-aaa",))}
        self.assertEqual(found, {"X-aaa.doc", "normal_analysis.doc"})

    def test_blank_extra_name_token_is_ignored(self) -> None:
        # An empty substring would match *every* Word doc — must be dropped.
        self._write_doc("source_data.doc")
        with self.assertLogs(nas.LOGGER, level="WARNING") as cm:
            results = nas.snapshot(
                self.root, STUB_CMD, dry_run=False, extra_names=["", "  "])
        self.assertEqual(results, [])
        self.assertFalse((self.root / "source_data.png").exists(),
                         "a blank token must not widen selection to every doc")
        self.assertTrue(any("blank --extra-name" in m for m in cm.output))

    def test_extra_name_png_only_sheet_gains_no_word_document(self) -> None:
        """An opted-in sheet rides the same no-synthesis rule as any other."""
        png = self.root / "X-aaa.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
        nas.snapshot(self.root, STUB_CMD, dry_run=False, extra_names=["X-aaa"])
        self.assertFalse(png.with_suffix(".docx").exists(),
                         "no sheet, opted-in or not, gains a fabricated .docx")

    def test_cli_extra_name_threads_through_main(self) -> None:
        doc = self._write_doc("Y-bbb.doc")
        rc = self._run(extra_names=["Y-bbb", "zzz"])  # repeatable; no-match is harmless
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "CLI --extra-name must reach snapshot() end-to-end")


# -----------------------------------------------------------------------------
# Known misspellings of the analysis token (e.g. ``analaysis.doc``)
# -----------------------------------------------------------------------------

class MisspellingTests(SnapshotTestBase):

    def test_misspelled_analysis_doc_produces_png(self) -> None:
        # ``analysis`` is not a substring of ``analaysis`` (extra 'a'), so the
        # plain token match misses it; the known-misspelling list must catch it.
        doc = self._write_doc("analaysis.doc")
        rc = self._run()
        self.assertEqual(rc, 0)
        self.assertTrue(doc.with_suffix(".png").exists(),
                        "a misspelled analysis sheet must still gain a .png")

    def test_iter_selects_misspelled_sheet_without_extra_name(self) -> None:
        self._write_doc("Gram 4 analaysis.doc")
        self._write_doc("source_data.doc")
        found = {p.name for p in nas.iter_analysis_sheets(self.root)}
        self.assertEqual(found, {"Gram 4 analaysis.doc"},
                         "misspelling is recognised out of the box, no --extra-name")

    def test_is_analysis_name_accepts_known_misspelling(self) -> None:
        self.assertTrue(nas._is_analysis_name("analaysis"))
        self.assertTrue(nas._is_analysis_name("Gram 4 ANALAYSIS"))
        self.assertFalse(nas._is_analysis_name("source_data"))


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

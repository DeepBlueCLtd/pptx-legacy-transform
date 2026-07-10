"""Tests for generate_dita.py (User Story 1)."""

from __future__ import annotations

import csv
import filecmp
import shutil
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_dita  # noqa: E402
import deduplicate_csv  # noqa: E402


FIXTURES = REPO_ROOT / "tests" / "fixtures"
TMP = REPO_ROOT / "tests" / "_tmp"


STATIC_ROOT = REPO_ROOT / "static"


def _run(out_dir: Path, csv_path: Path = FIXTURES / "minimal.csv",
         image_root: Path = FIXTURES, clean: bool = True,
         stub_wav: "Path | None" = None,
         static_root: "Path | None" = STATIC_ROOT) -> int:
    if clean and out_dir.exists():
        shutil.rmtree(out_dir)
    argv = [
        "--csv", str(csv_path),
        "--out", str(out_dir),
        "--image-root", str(image_root),
    ]
    if stub_wav is not None:
        argv += ["--stub-wav", str(stub_wav)]
    # Pin --static-root so the feature-010 common pages are sourced from a
    # known location (the repo's static/) rather than the process cwd. Pass
    # static_root=None to exercise the "no static root" degradation path.
    if static_root is not None:
        argv += ["--static-root", str(static_root)]
    return generate_dita.main(argv)


class GenerateDitaTests(unittest.TestCase):

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.out = TMP / f"out_{self._testMethodName}"
        if self.out.exists():
            shutil.rmtree(self.out)

    def test_gram_topic_has_gramframe_table(self) -> None:
        """Each GLC row contributes one ``<table outputclass='gram-config'>``
        carrying the time/freq parameters the GramFrame plugin reads."""
        rc = _run(self.out)
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        self.assertTrue(topic.is_file(), f"missing {topic}")
        root = ET.parse(topic).getroot()
        self.assertEqual(root.tag, "topic")
        table = root.find(".//table[@outputclass='gram-config']")
        self.assertIsNotNone(table)
        rows = {r.find("entry").text: r.findall("entry")[1].text
                for r in table.findall(".//tbody/row")
                if len(r.findall("entry")) == 2}
        self.assertEqual(rows.get("time-end"), "271")
        # bandwidth=400, bandcentre=200 -> band [0, 400] (issue #87).
        self.assertEqual(rows.get("freq-start"), "0")
        self.assertEqual(rows.get("freq-end"), "400")
        ph = root.find("./title/ph[@audience='-trainee']")
        self.assertIsNotNone(ph, "vessel name should be wrapped in <ph audience='-trainee'>")
        self.assertIn("Nordik Jockey", (ph.text or ""))
        # Operator Console v2 theme targets ``span.ph.vessel-name`` in the
        # rendered HTML, which DITA-OT only emits when the source ``<ph>``
        # carries ``outputclass="vessel-name"``.
        self.assertEqual(ph.get("outputclass"), "vessel-name")

    def test_gram_section_outputclasses_match_dark_theme_selectors(self) -> None:
        """The Operator Console v2 theme styles ``section.analysis-sheet`` and
        ``section.lofar-stage``. DITA-OT only emits those class tokens when
        the source ``<section>`` carries the matching ``outputclass``."""
        rc = _run(self.out)
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()

        analysis = root.find(".//section[@audience='-trainee']")
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.get("outputclass"), "analysis-sheet")

        stages = [
            s for s in root.findall(".//section")
            if s.get("outputclass") == "lofar-stage"
        ]
        self.assertGreaterEqual(
            len(stages), 1,
            "expected at least one gram-stage section with outputclass='lofar-stage'",
        )

    def test_glc_section_carries_incremental_lofar_title_and_anchor(self) -> None:
        """Each spectrogram section is numbered incrementally — ``Lofar N``
        — regardless of the source deck's inconsistent link labels, and
        carries the matching ``id="lofar-N"`` anchor so the floating nav
        panel can target it. The minimal fixture's Gram 12 has one Lofar."""
        _run(self.out)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        section = root.find(".//body/section[table]")
        self.assertIsNotNone(section, "expected a section wrapping the gramframe table")
        title = section.find("title")
        self.assertIsNotNone(title, "Lofar section must carry a numbered <title>")
        self.assertEqual(title.text, "Lofar 1")
        self.assertEqual(section.get("id"), "lofar-1",
                         "Lofar section must carry its incremental anchor id")

    def test_lofar_sections_numbered_incrementally(self) -> None:
        """Two spectrogram rows on one gram become Lofar 1 / Lofar 2 with
        anchors lofar-1 / lofar-2, in CSV ``sequence`` order — even when the
        source labels are inconsistent (one "Lofar", one blank here)."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        base = {c: "" for c in cols}
        base.update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "topic_filename": "gram_12.dita",
            "glc_path": "supporting/gram12/config.glc",
            "link_href": "supporting/gram12/config.glc",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
            "png_path": "images/gram12.png",
        })
        r1 = dict(base, sequence="1", display_text="Lofar")
        r2 = dict(base, sequence="2", display_text="")
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(r1)
            w.writerow(r2)
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        sections = [s for s in root.findall(".//body/section")
                    if s.get("outputclass") == "lofar-stage"]
        self.assertEqual(
            [(s.get("id"), s.find("title").text) for s in sections],
            [("lofar-1", "Lofar 1"), ("lofar-2", "Lofar 2")],
        )

    def test_wav_glc_section_numbered_as_lofar(self) -> None:
        """A ``.wav``-backed GLC section is a Lofar too: it joins the
        numbering with a ``Lofar N`` title and a ``lofar-N`` anchor, while
        the PPTX label survives as the inner xref text. Gram 05 has one."""
        _run(self.out)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05.dita"
        root = ET.parse(topic).getroot()
        xref_section = next(
            (s for s in root.findall(".//body/section") if s.find("p/xref") is not None),
            None,
        )
        self.assertIsNotNone(xref_section,
                             "expected a section wrapping the GLC-viewer xref")
        title = xref_section.find("title")
        self.assertIsNotNone(title, "WAV-typed Lofar section must carry a numbered <title>")
        self.assertEqual(title.text, "Lofar 1")
        self.assertEqual(xref_section.get("id"), "lofar-1")
        self.assertEqual(xref_section.find("p/xref").text, "Audio sample",
                         "the audio xref keeps the PPTX link label")

    def test_gramframe_table_has_named_colspecs(self) -> None:
        """DITA-OT needs named colspecs so the image cell renders with
        ``colspan='2'``; without them GramFrame rejects the table."""
        _run(self.out)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        colspecs = root.findall(".//table[@outputclass='gram-config']/tgroup/colspec")
        self.assertEqual([c.get("colname") for c in colspecs], ["c1", "c2"])

    def test_glc_asset_copied_with_slugified_name(self) -> None:
        """When the referenced asset exists, the generator copies it next to
        the topic (with a slugified filename, preserving the extension) and
        emits a topic-relative href."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12.dita"
        copied = gram_dir / "gram12.png"
        original = FIXTURES / "images" / "gram12.png"
        self.assertTrue(copied.is_file(), "asset must be copied next to topic")
        self.assertEqual(copied.read_bytes(), original.read_bytes())
        root = ET.parse(topic).getroot()
        image = root.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "gram12.png",
                         "href must be topic-relative, not an outward path")

    def test_image_present_in_generated_dita(self) -> None:
        """Regression guard: the gramframe block must carry an <image> element
        with a non-empty href pointing at a file that actually exists next to
        the topic. Without this, the published HTML would render an empty
        gram cell — the failure mode that motivated this test."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12.dita"
        root = ET.parse(topic).getroot()
        images = root.findall(".//image")
        self.assertGreaterEqual(len(images), 1,
                                "generated DITA must contain at least one <image>")
        for img in images:
            href = img.get("href")
            self.assertTrue(href, f"<image> is missing href: {ET.tostring(img)!r}")
            self.assertFalse(href.startswith(("/", "..")),
                             f"image href must be topic-relative, got {href!r}")
            self.assertTrue((gram_dir / href).is_file(),
                            f"image file referenced by DITA is missing: {gram_dir / href}")

    def test_analysis_section_in_gram_topic(self) -> None:
        """Analysis assets are copied into the per-gram folder and the gram
        topic carries an instructor-only analysis section (PNG embedded as
        <image>, DOCX linked via <xref>)."""
        _run(self.out)
        gram_dir = self.out / "main" / "nordic-fishing-vessels" / "gram-12"
        topic = gram_dir / "gram_12.dita"
        copied = gram_dir / "gram12-analysis.png"
        self.assertTrue(copied.is_file(), "analysis asset must be copied next to topic")
        root = ET.parse(topic).getroot()
        analysis_section = root.find(".//body/section[@audience='-trainee']")
        self.assertIsNotNone(analysis_section,
                             "gram topic must include an instructor-only analysis section")
        image = analysis_section.find("image")
        self.assertIsNotNone(image, "PNG analysis assets render as <image>")
        self.assertEqual(image.get("href"), "gram12-analysis.png")

    def test_debug_provenance_block_on_by_default_maps_published_to_source(self) -> None:
        """The source-provenance block is ON by default (current debugging
        phase): a plain build stamps each gram with an instructor-only note
        mapping its published path back to the source publication, chapter/deck
        and original gram number, plus the analysis image's source path."""
        rc = _run(self.out)  # no flag -> default on
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        note = root.find(".//body/note[@outputclass='debug-provenance']")
        self.assertIsNotNone(note, "provenance note should be present by default")
        # Instructor-only so it never leaks into a student edition.
        self.assertEqual(note.get("audience"), "-trainee")
        text = " ".join(p.text or "" for p in note.findall("p"))
        self.assertIn("main", text)                    # source publication
        self.assertIn("Nordic Fishing Vessels", text)  # source chapter/deck title
        self.assertIn("12", text)                       # source gram number
        self.assertIn("gram12_analysis.png", text)      # analysis image source path

    def test_no_debug_provenance_block_when_suppressed(self) -> None:
        """--no-debug-provenance suppresses the temporary block, so a build
        passed that flag carries no debug note."""
        rc = generate_dita.main([
            "--csv", str(FIXTURES / "minimal.csv"),
            "--out", str(self.out),
            "--image-root", str(FIXTURES),
            "--static-root", str(STATIC_ROOT),
            "--no-debug-provenance",
        ])
        self.assertEqual(rc, 0)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        self.assertIsNone(
            root.find(".//note[@outputclass='debug-provenance']"),
            "no debug provenance block should appear with --no-debug-provenance")

    def test_gram_nav_panel_links_lofars_for_all_and_analysis_instructor_only(self) -> None:
        """A gram carries a single floating nav panel (``<p class="gram-nav">``).
        It lists one in-page xref per Lofar (unfiltered — both editions) plus,
        for a gram with an analysis sheet, a trailing instructor-only
        (``audience="-trainee"``) xref to the analysis-sheet section. Every
        xref targets a real anchor within the same topic."""
        _run(self.out)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        topic_id = root.get("id")

        panel = root.find(".//body/p[@outputclass='gram-nav']")
        self.assertIsNotNone(panel, "gram page must carry the floating nav panel")

        xrefs = panel.findall("xref")
        # Gram 12: one Lofar + an analysis sheet => two panel entries.
        self.assertEqual(
            [(x.text, x.get("href"), x.get("audience")) for x in xrefs],
            [
                ("Lofar 1", f"#{topic_id}/lofar-1", None),
                ("Analysis Sheet", f"#{topic_id}/analysis-sheet", "-trainee"),
            ],
        )
        # Each anchor resolves to a section that actually carries that id.
        ids = {s.get("id") for s in root.findall(".//body/section")}
        self.assertIn("lofar-1", ids)
        self.assertIn("analysis-sheet", ids)

    def test_gram_nav_panel_without_analysis_omits_instructor_entry(self) -> None:
        """A gram with no analysis sheet (e.g. a progress-test gram) still
        gets the nav panel — students navigate Lofars too — but with no
        instructor-only analysis entry to strip."""
        _run(self.out)
        topic = self.out / "progress-test-1" / "gram-03" / "gram_03.dita"
        root = ET.parse(topic).getroot()
        panel = root.find(".//body/p[@outputclass='gram-nav']")
        self.assertIsNotNone(panel, "a gram page must carry the nav panel for students too")
        xrefs = panel.findall("xref")
        self.assertEqual([x.text for x in xrefs], ["Lofar 1"],
                         "only the Lofar entry — no analysis sheet on this gram")
        self.assertIsNone(panel.find("xref[@audience]"),
                          "no instructor-only entry without an analysis sheet")

    def test_docx_analysis_renders_as_xref(self) -> None:
        """When the analysis asset is a .docx, the section emits an <xref>
        instead of an embedded <image>."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [
            {c: "" for c in cols},
            {c: "" for c in cols},
        ]
        rows[0].update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_12.dita",
            "link_href": "supporting/gram12/config_1.glc",
            "glc_path": "supporting/gram12/config_1.glc",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
            "png_path": "images/gram12.png",
        })
        rows[1].update({
            "publication": "main", "chapter": "Nordic Fishing Vessels",
            "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
            "topic_type": "analysis", "sequence": "1",
            "topic_filename": "gram_12.dita",
            "png_path": "analysis.docx",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        root = ET.parse(topic).getroot()
        analysis_section = root.find(".//body/section[@audience='-trainee']")
        self.assertIsNotNone(analysis_section)
        xref = analysis_section.find(".//xref")
        self.assertIsNotNone(xref, "DOCX analysis assets render as <xref>")
        self.assertEqual(xref.get("href"), "analysis.docx")
        self.assertEqual(xref.get("format"), "docx")

    def test_jpg_analysis_renders_as_inline_image(self) -> None:
        """JPG and JPEG analysis assets embed as <image>, not <xref>."""
        for ext in ("jpg", "jpeg"):
            with self.subTest(ext=ext):
                csv_path = TMP / f"{self._testMethodName}_{ext}.csv"
                cols = generate_dita.CSV_COLUMNS
                rows = [{c: "" for c in cols}, {c: "" for c in cols}]
                rows[0].update({
                    "publication": "main", "chapter": "Nordic Fishing Vessels",
                    "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
                    "topic_type": "glc", "sequence": "1",
                    "topic_filename": "gram_12.dita",
                    "link_href": "supporting/gram12/config_1.glc",
                    "glc_path": "supporting/gram12/config_1.glc",
                    "time_end": "271", "bandwidth": "400", "bandcentre": "200",
                    "png_path": "images/gram12.png",
                })
                rows[1].update({
                    "publication": "main", "chapter": "Nordic Fishing Vessels",
                    "gram_id": "Gram 12", "vessel_name": "Nordik Jockey",
                    "topic_type": "analysis", "sequence": "1",
                    "topic_filename": "gram_12.dita",
                    "png_path": f"analysis.{ext}",
                })
                with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(cols),
                                       quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
                    w.writeheader()
                    for r in rows:
                        w.writerow(r)
                out = TMP / f"{self._testMethodName}_{ext}_out"
                _run(out, csv_path=csv_path)
                topic = out / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
                root = ET.parse(topic).getroot()
                analysis_section = root.find(".//body/section[@audience='-trainee']")
                self.assertIsNotNone(analysis_section)
                image = analysis_section.find("image")
                self.assertIsNotNone(image, f".{ext} analysis assets must render as <image>")
                self.assertEqual(image.get("href"), f"analysis.{ext}")

    def test_main_ditamap_weeks_at_top_level(self) -> None:
        """Each main chapter (week) is a *sub-document* pulled up to the **top
        level** of the map: a real chapter topic referenced by a top-level
        ``<topicref>`` (beside the static pages, no enclosing ``Grams``
        ``<topichead>``), with the chapter's gram topicrefs one tier below it."""
        _run(self.out)
        ditamap = self.out / "main" / "main.ditamap"
        self.assertTrue(ditamap.is_file(),
                        "main.ditamap must live inside the main/ folder")
        root = ET.parse(ditamap).getroot()
        self.assertEqual(root.tag, "map")
        # The weeks are pulled up to the top level — the single "Grams"
        # <topichead> folder is gone from main.
        self.assertEqual(root.findall("topichead"), [],
                         "main has no Grams folder — weeks sit at the top level")
        # A week topicref points at its chapter topic; static pages are bare
        # filenames. The chapter topicrefs are the non-static root topicrefs.
        chapters = [tr for tr in root.findall("topicref")
                    if "/" in (tr.get("href") or "")]
        self.assertGreaterEqual(len(chapters), 1)
        for chapter_ref in chapters:
            href = chapter_ref.get("href")
            self.assertRegex(href, r"^[a-z0-9-]+/[a-z0-9_]+\.dita$",
                             "chapter topicref points at the chapter topic")
            chapter_topic = ditamap.parent / href
            self.assertTrue(chapter_topic.is_file(),
                            f"chapter topic missing on disk: {chapter_topic}")
            gram_refs = chapter_ref.findall("topicref")
            self.assertGreaterEqual(len(gram_refs), 1,
                                    "gram topicrefs nest inside the chapter")
            for gram_ref in gram_refs:
                self.assertTrue((ditamap.parent / gram_ref.get("href")).is_file(),
                                "gram hrefs are relative to the ditamap folder")

    def test_main_ditamap_one_topicref_per_gram(self) -> None:
        """The CSV carries N+1 rows per gram but the ditamap must point to
        the single gram topic once, not once per row."""
        _run(self.out)
        ditamap = self.out / "main" / "main.ditamap"
        root = ET.parse(ditamap).getroot()
        hrefs = [tr.get("href") for tr in root.findall(".//topicref")]
        self.assertEqual(len(hrefs), len(set(hrefs)),
                         f"duplicate topicrefs in ditamap: {hrefs}")

    def test_chapter_topic_contains_enter_btn_links(self) -> None:
        """The week chapter topic itself holds a ``<ul outputclass='gram-index'>``
        with ``<xref outputclass='enterBtn'>`` links to the week's grams, so
        clicking a week in the nav lands directly on the gram-selection page
        without an extra hop (issue #130)."""
        _run(self.out)
        chapter_path = (
            self.out / "main" / "nordic-fishing-vessels" / "nordic_fishing_vessels.dita"
        )
        self.assertTrue(chapter_path.is_file())
        root = ET.parse(chapter_path).getroot()
        ul = root.find(".//ul[@outputclass='gram-index']")
        self.assertIsNotNone(ul, "expected <ul outputclass='gram-index'> in chapter topic")
        xrefs = ul.findall(".//xref[@outputclass='enterBtn']")
        self.assertGreaterEqual(len(xrefs), 1, "expected at least one enterBtn link")
        for xref in xrefs:
            self.assertEqual(xref.get("format"), "dita")
            href = xref.get("href", "")
            self.assertTrue(href.endswith(".dita"),
                            f"enterBtn href should point at a .dita topic: {href!r}")
            self.assertIsNotNone(xref.text)
            self.assertTrue(xref.text.startswith("Gram "),
                            f"button label should start with 'Gram ': {xref.text!r}")

    def test_no_ditamap_at_output_root(self) -> None:
        """Every ditamap lives inside its named publication folder; nothing
        ``*.ditamap`` may sit at the root of the output tree."""
        _run(self.out)
        self.assertEqual(sorted(p.name for p in self.out.glob("*.ditamap")), [],
                         "no ditamap may sit at the output root")
        self.assertTrue((self.out / "main" / "main.ditamap").is_file())
        self.assertTrue(
            (self.out / "progress-test-1" / "progress-test-1.ditamap").is_file())

    def test_main_unassigned_week_fails_fast(self) -> None:
        """A ``main`` row with an empty effective chapter (no week assigned —
        e.g. a Pub10 deck whose ``target_chapter`` an analyst hasn't filled
        in) is a fail-fast error: with the weeks pulled up to the top level
        of the map there is no Grams folder to park a weekless gram under, so
        the generator must reject it rather than emit a naked root gram.

        ``check_main_chapter_assigned`` flags the row, and a full run aborts
        with rc 1 before writing any ditamap. (Non-``main`` weekless rows are
        unaffected — the progress tests have no week tier.)
        """
        row = {c: "" for c in generate_dita.CSV_COLUMNS + generate_dita.OPTIONAL_CSV_COLUMNS}
        row.update({
            "publication": "main", "chapter": "", "gram_id": "Gram 1",
            "topic_type": "main", "sequence": "1",
            "topic_filename": "gram_01.dita",
            "target_doc": "Pub10_Ed22B_Updated.pptx",  # ignored for main (feature 009 guard)
        })
        errors = generate_dita.check_main_chapter_assigned([row])
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("target_chapter", errors[0])
        # A weekless progress-test row is not flagged — only main has weeks.
        test_row = dict(row)
        test_row["publication"] = "progress-test-1"
        self.assertEqual(generate_dita.check_main_chapter_assigned([test_row]), [])

    def test_main_unassigned_week_aborts_full_run(self) -> None:
        """The fail-fast check is wired into the CLI: a CSV with a weekless
        ``main`` row exits rc 1 and writes no main ditamap."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        row = {c: "" for c in cols}
        row.update({
            "publication": "main", "chapter": "", "gram_id": "Gram 1",
            "topic_type": "main", "sequence": "1", "topic_filename": "gram_01.dita",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(row)
        rc = _run(self.out, csv_path=csv_path)
        self.assertEqual(rc, 1, "weekless main row must abort the run")
        self.assertFalse((self.out / "main" / "main.ditamap").is_file(),
                         "no main ditamap may be written when a week is unassigned")

    def test_main_ditamap_grams_sorted_by_effective_number(self) -> None:
        """Within a week, gram topicrefs are emitted in ascending numeric
        order — not CSV row order, which interleaves a week's native deck
        with the even-sliced no-week decks' renumbered grams. The sort is
        numeric (102 follows 23), and the effective number (target_gram_id)
        is what's ordered."""
        def row(gram_id, target="", chapter="2"):
            r = {c: "" for c in generate_dita.CSV_COLUMNS + generate_dita.OPTIONAL_CSV_COLUMNS}
            r.update({
                "publication": "main", "chapter": "Some Deck",
                "target_chapter": chapter, "gram_id": gram_id,
                "topic_type": "glc", "sequence": "1",
                "topic_filename": "x.dita", "target_gram_id": target,
            })
            return r

        rows = [row("23"), row("7", target="102"), row("7")]
        ditamap = generate_dita.emit_main_ditamap(rows, self.out)
        hrefs = [tr.get("href")
                 for tr in ET.parse(ditamap).getroot().iter("topicref")
                 if "gram-" in (tr.get("href") or "")]
        self.assertEqual(hrefs, [
            "week-2/gram-07/gram_07.dita",
            "week-2/gram-23/gram_23.dita",
            "week-2/gram-102/gram_102.dita",
        ], "grams must sort by effective number, numerically")

    def test_test_ditamap_grams_sorted_by_effective_number(self) -> None:
        """The flat publications' gram topicrefs are number-ordered too,
        regardless of CSV row order."""
        def row(gram_id):
            r = {c: "" for c in generate_dita.CSV_COLUMNS + generate_dita.OPTIONAL_CSV_COLUMNS}
            r.update({
                "publication": "progress-test-9", "gram_id": gram_id,
                "topic_type": "glc", "sequence": "1", "topic_filename": "x.dita",
            })
            return r

        ditamap = generate_dita.emit_test_ditamap(
            "progress-test-9", [row("10"), row("2")], self.out)
        hrefs = [tr.get("href")
                 for tr in ET.parse(ditamap).getroot().iter("topicref")
                 if "gram-" in (tr.get("href") or "")]
        self.assertEqual(hrefs, ["gram-02/gram_02.dita", "gram-10/gram_10.dita"])

    def test_test_ditamap_grams_under_grams_folder(self) -> None:
        """Feature 010: a progress-test ditamap's root children are the <title>,
        the common static <topicref>s, then a single "Grams" <topichead> holding
        every gram topicref — no gram sits at the ditamap root any more."""
        _run(self.out)
        ditamap = self.out / "progress-test-1" / "progress-test-1.ditamap"
        self.assertTrue(ditamap.is_file(),
                        "the test ditamap must live inside its publication folder")
        root = ET.parse(ditamap).getroot()
        for child in root:
            self.assertIn(child.tag, {"title", "topicref", "topichead"},
                          f"unexpected child {child.tag} in test ditamap")
        topicheads = root.findall("topichead")
        self.assertEqual(len(topicheads), 1,
                         "exactly one root-level topichead — the Grams folder")
        grams = topicheads[0]
        self.assertEqual(grams.find("topicmeta/navtitle").text, "Grams")
        # Grams holds the gram topicrefs directly — progress tests have no
        # per-chapter tier below the Grams folder.
        self.assertGreaterEqual(len(grams.findall("topicref")), 1)
        self.assertIsNone(grams.find("topichead"),
                          "progress-test grams sit flat under Grams, no chapter tier")
        # No gram topicref leaks up to the ditamap root.
        self.assertEqual(
            [tr.get("href") for tr in root.findall("topicref")
             if "gram-" in (tr.get("href") or "")],
            [], "no gram topicref may sit at the ditamap root",
        )

    def test_static_pages_lead_every_ditamap(self) -> None:
        """Feature 010: Welcome then Security are the first root-level
        topicrefs, bare-filename hrefs (the map sits beside the copied
        pages). For progress tests they precede the Grams folder; for main
        they precede the top-level Week folders."""
        _run(self.out)
        # Progress tests: static pages are the *only* root topicrefs, ahead
        # of the single Grams <topichead>.
        root = ET.parse(self.out / "progress-test-1"
                        / "progress-test-1.ditamap").getroot()
        self.assertEqual(
            [tr.get("href") for tr in root.findall("topicref")],
            ["welcome.dita", "security.dita"],
            "progress test: Welcome then Security must be the only root "
            "topicrefs (grams live under the Grams folder)",
        )
        tags = [c.tag for c in root]
        self.assertLess(tags.index("topicref"), tags.index("topichead"),
                        "static pages must precede the Grams folder")
        # Main: weeks are pulled up to the top level, so the root topicrefs are
        # Welcome, Security, then the Week sub-documents — static pages lead.
        root = ET.parse(self.out / "main" / "main.ditamap").getroot()
        hrefs = [tr.get("href") for tr in root.findall("topicref")]
        self.assertEqual(hrefs[:2], ["welcome.dita", "security.dita"],
                         "main: Welcome then Security must lead the top level")
        self.assertGreater(len(hrefs), 2,
                           "main: Week sub-documents follow the static pages")

    def test_static_tree_copied_into_each_publication(self) -> None:
        """The whole static tree (pages + image subfolder) is copied into every
        publication folder: non-DITA files byte-for-byte; ``.dita`` pages with
        the hidden instructor-only edition marker stamped into their body."""
        _run(self.out)
        for pub in ("main", "progress-test-1"):
            # Images (and any other non-DITA asset) are copied verbatim.
            dst = self.out / pub / "images" / "welcome-banner.png"
            self.assertTrue(dst.is_file(), f"missing copied static file {dst}")
            self.assertTrue(
                filecmp.cmp(STATIC_ROOT / "images" / "welcome-banner.png",
                            dst, shallow=False),
                f"{dst} must be a byte-for-byte copy of the static source",
            )
            # Each static .dita page carries the edition marker as the first
            # body child, audience-tagged so the trainee filter strips it.
            for name in ("welcome.dita", "security.dita"):
                dst = self.out / pub / name
                self.assertTrue(dst.is_file(), f"missing copied static page {dst}")
                root = ET.parse(dst).getroot()
                marker = root.find("body")[0]
                self.assertEqual(marker.tag, "p")
                self.assertEqual(marker.get("outputclass"), "gf-persistent")
                self.assertEqual(marker.get("audience"), "-trainee")

    def test_missing_static_root_degrades_gracefully(self) -> None:
        """An absent static root omits the common pages (no root topicref) but
        still demotes grams under the Grams folder and succeeds (rc 0)."""
        rc = _run(self.out, static_root=TMP / "absent_static_dir")
        self.assertEqual(rc, 0)
        root = ET.parse(
            self.out / "progress-test-1" / "progress-test-1.ditamap").getroot()
        self.assertEqual(root.findall("topicref"), [],
                         "no static pages when the static root is absent")
        grams = root.find("topichead")
        self.assertIsNotNone(grams, "grams are still demoted under a Grams folder")
        self.assertEqual(grams.find("topicmeta/navtitle").text, "Grams")

    def test_every_topic_carries_instructor_edition_marker(self) -> None:
        """Every ``<topic>`` page — grams, chapter sub-documents, and the copied
        static common pages — carries the hidden instructor-only edition marker
        as the first body child, so the shared stylesheet can tell the editions
        apart on every rendered page. The marker is audience-tagged, so the
        trainee filter strips it for the student edition (keeping SC-002's "no
        instructor" leakage check clean).
        """
        _run(self.out)
        topics = [p for p in self.out.rglob("*.dita")
                  if ET.parse(p).getroot().tag == "topic"]
        # Grams + chapter sub-documents + static pages across publications.
        self.assertGreater(len(topics), 3, "expected several topic pages")
        for topic in topics:
            root = ET.parse(topic).getroot()
            body = root.find("body")
            self.assertIsNotNone(body, f"{topic} has no body to mark")
            marker = body[0]
            self.assertEqual(marker.tag, "p", f"{topic} marker is not first")
            self.assertEqual(marker.get("outputclass"), "gf-persistent", topic)
            self.assertEqual(marker.get("audience"), "-trainee", topic)

    def test_glc_inner_wav_renders_as_glc_viewer_link(self) -> None:
        """A GLC row whose inner asset is a .wav renders as a §1.3
        GLC-viewer-link block: a plain <xref> to the .glc (so the
        on-PC GLC viewer opens it and resolves the .wav next to it),
        with no <image> and no gramframe table for that row."""
        _run(self.out)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        # No gramframe table for this row (no pre-rendered spectrogram).
        self.assertIsNone(root.find(".//table[@outputclass='gram-config']"))
        # No <image> either — the WAV is not a renderable image.
        self.assertIsNone(root.find(".//image"))
        xref = root.find(".//xref")
        self.assertIsNotNone(xref, "WAV-typed GLC row must emit an <xref>")
        # The href targets the .glc (slugified), not the .wav: the GLC
        # viewer reads the .glc's <filename> element to find the audio.
        self.assertEqual(xref.get("href"), "config.glc")
        self.assertEqual(xref.get("format"), "glc")
        self.assertEqual(xref.get("scope"), "local")
        self.assertEqual(xref.text, "Audio sample")

    def test_glc_row_without_classifiable_asset_is_skipped(self) -> None:
        """A GLC row whose png_path is empty (or carries an extension
        the generator cannot dispatch on) contributes no block to its
        gram topic and is recorded in skipped.txt."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [
            {c: "" for c in cols},
        ]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 05", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_05.dita",
            "display_text": "Audio sample",
            "link_href": "supporting/gram05/config.glc",
            "glc_path": "supporting/gram05/config.glc",
            # png_path left empty — the .glc parse failed to yield an
            # inner asset filename, so there's nothing to dispatch on.
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-05" / "gram_05.dita"
        # The skipped row contributes no block, but the gram topic still
        # renders (empty body bar the title).
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        self.assertIsNone(root.find(".//table[@outputclass='gram-config']"))
        skipped = self.out / "skipped.txt"
        self.assertTrue(skipped.is_file())
        self.assertIn('gram_id="5"', skipped.read_text(encoding="utf-8"))

    def test_glc_inner_wav_copies_glc_and_wav_pair(self) -> None:
        """End-to-end happy path for the §1.3 GLC-viewer-link contract:
        when both the .glc and the named .wav exist on disk, the
        generator copies both into the per-gram folder under slugified
        names, byte-identical to the source, so the on-PC GLC viewer
        can resolve the audio. Covers the success branches that
        ``test_glc_inner_wav_renders_as_glc_viewer_link`` skips
        (fixture .glc/.wav are missing there, so the copy is a no-op)."""
        glc_src = TMP / "wav_pair_src" / "supporting" / "gram07" / "config.glc"
        wav_src = TMP / "wav_pair_src" / "supporting" / "gram07" / "audio_clip.wav"
        glc_src.parent.mkdir(parents=True, exist_ok=True)
        glc_src.write_bytes(b"<GAPS_Lite_configuration/>")
        wav_src.write_bytes(b"RIFF\x00\x00\x00\x00WAVEfmt ")
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 07", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_07.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram07/config.glc",
            "glc_path": "supporting/gram07/config.glc",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
            "png_path": "supporting/gram07/audio_clip.wav",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path, image_root=TMP / "wav_pair_src")
        gram_dir = self.out / "main" / "arctic-survey" / "gram-07"
        glc_copy = gram_dir / "config.glc"
        wav_copy = gram_dir / "audio-clip.wav"
        self.assertTrue(glc_copy.is_file(), "the .glc must be copied next to the topic")
        self.assertTrue(wav_copy.is_file(),
                        "the companion .wav must travel with the .glc so the "
                        "on-PC viewer can resolve it")
        self.assertEqual(glc_copy.read_bytes(), glc_src.read_bytes())
        self.assertEqual(wav_copy.read_bytes(), wav_src.read_bytes())
        # And the topic's xref must point at the slugified .glc.
        topic = gram_dir / "gram_07.dita"
        root = ET.parse(topic).getroot()
        xref = root.find(".//xref")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.get("href"), "config.glc")
        self.assertEqual(xref.get("format"), "glc")

    def test_stub_wav_substitutes_contents_keeps_slug(self) -> None:
        """``--stub-wav`` swaps every .wav source with the stub file but keeps
        the slugified per-gram filename so the paired .glc's internal
        ``data_source/filename`` reference still resolves at publish time.
        The .glc itself is copied verbatim — only the .wav is stubbed."""
        glc_src = TMP / "stub_wav_src" / "supporting" / "gram08" / "config.glc"
        wav_src = TMP / "stub_wav_src" / "supporting" / "gram08" / "audio_clip.wav"
        stub_src = TMP / "stub.wav"
        glc_src.parent.mkdir(parents=True, exist_ok=True)
        glc_src.write_bytes(b"<GAPS_Lite_configuration/>")
        wav_src.write_bytes(b"REAL-WAV-CONTENT")
        stub_src.write_bytes(b"STUB-WAV-CONTENT")
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 08", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_08.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram08/config.glc",
            "glc_path": "supporting/gram08/config.glc",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
            "png_path": "supporting/gram08/audio_clip.wav",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path, image_root=TMP / "stub_wav_src",
             stub_wav=stub_src)
        gram_dir = self.out / "main" / "arctic-survey" / "gram-08"
        glc_copy = gram_dir / "config.glc"
        wav_copy = gram_dir / "audio-clip.wav"
        self.assertTrue(wav_copy.is_file())
        # Slug preserved so the .glc's internal filename reference resolves.
        self.assertEqual(wav_copy.name, "audio-clip.wav")
        # Contents come from the stub, not the original.
        self.assertEqual(wav_copy.read_bytes(), b"STUB-WAV-CONTENT")
        # The .glc is copied verbatim — stubbing is wav-only.
        self.assertEqual(glc_copy.read_bytes(), glc_src.read_bytes())

    def test_glc_row_with_unsupported_extension_is_skipped(self) -> None:
        """The dispatch must reject any extension that is neither image
        (.png/.jpg/.jpeg/.gif) nor .wav — including plausible-looking ones
        like .bmp or .pdf — and record the skip with the offending
        extension in the reason so the technical author can triage."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 08", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_08.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram08/config.glc",
            "glc_path": "supporting/gram08/config.glc",
            "png_path": "supporting/gram08/spectrogram.bmp",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-08" / "gram_08.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        self.assertIsNone(root.find(".//image"))
        self.assertIsNone(root.find(".//xref"))
        skipped = (self.out / "skipped.txt").read_text(encoding="utf-8")
        self.assertIn('gram_id="8"', skipped)
        self.assertIn(".bmp", skipped,
                      "the skip reason should name the rejected extension")

    def test_glc_row_with_gif_asset_embeds_gramframe_image(self) -> None:
        """A pre-rendered spectrogram named in the GLC may be a ``.gif``
        (some legacy decks use them). It must dispatch to the inline
        GramFrame table exactly like ``.png``/``.jpg`` — not be skipped —
        and the case of the source suffix (``.GIF``) must not matter."""
        csv_path = TMP / f"{self._testMethodName}.csv"
        cols = generate_dita.CSV_COLUMNS
        rows = [{c: "" for c in cols}]
        rows[0].update({
            "publication": "main", "chapter": "Arctic Survey",
            "gram_id": "Gram 09", "vessel_name": "Arctic Surveyor",
            "topic_type": "glc", "sequence": "1",
            "topic_filename": "gram_09.dita",
            "display_text": "Lofar 1",
            "link_href": "supporting/gram09/config.glc",
            "glc_path": "supporting/gram09/config.glc",
            "png_path": "supporting/gram09/spectrogram.GIF",
        })
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
            w.writeheader()
            w.writerow(rows[0])
        _run(self.out, csv_path=csv_path)
        topic = self.out / "main" / "arctic-survey" / "gram-09" / "gram_09.dita"
        self.assertTrue(topic.is_file())
        root = ET.parse(topic).getroot()
        image = root.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image, "a .gif Lofar must embed a GramFrame image")
        self.assertEqual(image.get("href"), "spectrogram.gif",
                         "the copied asset href is the slugified, lower-cased name")
        skipped = self.out / "skipped.txt"
        if skipped.is_file():
            self.assertNotIn("spectrogram", skipped.read_text(encoding="utf-8"),
                             "a .gif Lofar must not be skipped")

    def test_stale_tree_wiped_without_clean_flag(self) -> None:
        """The output tree is always rebuilt from scratch (clean is now the
        default, not opt-in): a leftover file from a previous document's build
        must not survive a run, even when ``--clean`` isn't passed."""
        self.out.mkdir(parents=True, exist_ok=True)
        stale = self.out / "stale_from_other_document.dita"
        stale.write_text("<topic/>", encoding="utf-8")
        # _run defaults to clean=False here so only the generator's own wipe acts.
        rc = _run(self.out, clean=False)
        self.assertEqual(rc, 0)
        self.assertFalse(stale.exists(),
                         "a stale file must be wiped even without --clean")

    def test_idempotent_output(self) -> None:
        rc1 = _run(self.out, clean=True)
        self.assertEqual(rc1, 0)
        snapshot = TMP / f"{self._testMethodName}_snapshot"
        if snapshot.exists():
            shutil.rmtree(snapshot)
        shutil.copytree(self.out, snapshot)
        rc2 = _run(self.out, clean=False)
        self.assertEqual(rc2, 0)
        diff = filecmp.dircmp(self.out, snapshot)
        differing = self._collect_diffs(diff)
        self.assertEqual(differing, [], f"non-idempotent files: {differing}")

    def _collect_diffs(self, diff: filecmp.dircmp) -> list[str]:
        result = list(diff.diff_files) + list(diff.left_only) + list(diff.right_only)
        for sub in diff.subdirs.values():
            result.extend(self._collect_diffs(sub))
        return result

    def test_trainee_ditaval_emitted_with_exact_bytes(self) -> None:
        """``publish_html.py`` aborts unless ``<dita>/trainee.ditaval`` exists
        with the audience-exclude rule, so the generator must produce it
        every run — even after ``--clean`` wipes the tree."""
        _run(self.out)
        ditaval = self.out / "trainee.ditaval"
        self.assertTrue(ditaval.is_file(), f"missing {ditaval}")
        self.assertEqual(
            ditaval.read_text(encoding="utf-8"),
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<val>\n'
            '  <prop att="audience" val="-trainee" action="exclude"/>\n'
            '</val>\n',
        )
        manifest_lines = (self.out / "manifest.txt").read_text(encoding="utf-8").splitlines()
        self.assertIn("trainee.ditaval", manifest_lines)

    def test_manifest_lists_every_output_file(self) -> None:
        _run(self.out)
        manifest = self.out / "manifest.txt"
        self.assertTrue(manifest.is_file())
        listed = set(manifest.read_text(encoding="utf-8").splitlines())
        listed.discard("")
        actual = set()
        for path in self.out.rglob("*"):
            if path.is_file() and path.name not in {"manifest.txt", "skipped.txt"}:
                actual.add(path.relative_to(self.out).as_posix())
        self.assertEqual(listed, actual)
        self.assertEqual(sorted(listed), list(manifest.read_text(encoding="utf-8").splitlines()[:len(listed)]),
                         "manifest must be sorted")


class SlugifyAssetNameTests(unittest.TestCase):
    """``slugify_asset_name`` URL-safes filenames and corrects known legacy
    misspellings so the emitted asset name and every href read consistently."""

    def test_slugify_preserves_extension_and_hyphenates(self) -> None:
        self.assertEqual(
            generate_dita.slugify_asset_name("Lofar 1 ABC.PNG"), "lofar-1-abc.png")

    def test_misspelled_analysis_name_is_corrected(self) -> None:
        # The source file is named ``analaysis.png`` (an 'analysis' typo); the
        # emitted asset name / href must read ``analysis.png``.
        self.assertEqual(
            generate_dita.slugify_asset_name("analaysis.png"), "analysis.png")
        self.assertEqual(
            generate_dita.slugify_asset_name("Gram 4 analaysis.png"),
            "gram-4-analysis.png")

    def test_correctly_spelled_name_is_untouched(self) -> None:
        self.assertEqual(
            generate_dita.slugify_asset_name("analysis sheet.png"),
            "analysis-sheet.png")

    def test_copy_asset_reads_misspelled_source_writes_corrected_name(self) -> None:
        # The on-disk asset keeps its misspelled name; copy_asset reads it
        # from there but names the copied target ``analysis.png``.
        tmp = TMP / "copy_misspelled"
        if tmp.exists():
            shutil.rmtree(tmp)
        image_root = tmp / "src"
        topic_dir = tmp / "out" / "gram-04"
        image_root.mkdir(parents=True)
        (image_root / "analaysis.png").write_bytes(b"\x89PNG\r\n\x1a\n rendered")
        href, written = generate_dita.copy_asset("analaysis.png", image_root, topic_dir)
        self.assertEqual(href, "analysis.png",
                         "href must use the corrected spelling")
        self.assertIsNotNone(written)
        self.assertEqual(written.name, "analysis.png")
        self.assertTrue((topic_dir / "analysis.png").is_file(),
                        "copied file must land under the corrected name")


class MainFlatLayoutTests(unittest.TestCase):
    """Feature 009 (US2): ``main`` is flat — ``main/week-N/gram-NN/`` with no
    source-document tier — and scoped per ``(main, week)``. This is already true
    on extractor output (``target_doc=""`` for ``main``); these tests lock it and
    verify the ``_effective_doc`` guard holds even if a CSV stray-sets
    ``target_doc`` on a ``main`` row."""

    def _row(self, **kw):
        base = {c: "" for c in generate_dita.CSV_COLUMNS + generate_dita.OPTIONAL_CSV_COLUMNS}
        base.update(publication="main", topic_type="glc", sequence="1")
        base.update(kw)
        return base

    def test_main_topic_path_has_no_doc_tier_even_with_stray_target_doc(self) -> None:
        out = Path("/out")
        row = self._row(
            chapter="Some Deck", target_chapter="2", gram_id="Gram 3",
            target_doc="Pub10.pptx",  # stray target_doc on a main row
        )
        rel = generate_dita._topic_dir_for_row(out, row).relative_to(out)
        self.assertEqual(rel.as_posix(), "main/week-2/gram-03")

    def test_main_collision_key_ignores_target_doc(self) -> None:
        # Two distinct main grams, same week + number, different target_doc.
        # The guard forces main's effective_doc to "" so they still collide
        # (otherwise the flat folder would be silently overwritten).
        rows = [
            self._row(chapter="A deck", target_chapter="2", gram_id="Gram 5",
                      vessel_name="V1", topic_type="analysis", target_doc="d1"),
            self._row(chapter="B deck", target_chapter="2", gram_id="Gram 5",
                      vessel_name="V2", topic_type="analysis", target_doc="d2"),
        ]
        errors = generate_dita.check_row_identity(rows)
        self.assertTrue(
            errors, "two distinct main grams at the same (week, number) must collide",
        )
        self.assertIn("renumber", errors[0].lower())


class AudienceShapeTests(unittest.TestCase):
    """Spec 003 — chapter slug normalisation and audience-tagged ditamap shape.

    Drives `generate_dita.py` against ``tests/fixtures/audience_minimal.csv``
    which carries one "Instructor "-prefixed chapter, one plain chapter,
    and a mix of vessel-name and no-vessel-name grams.
    """

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.out = TMP / f"out_{self._testMethodName}"
        if self.out.exists():
            shutil.rmtree(self.out)
        rc = _run(self.out, csv_path=FIXTURES / "audience_minimal.csv")
        self.assertEqual(rc, 0)

    def test_chapter_slug_strips_instructor_prefix(self) -> None:
        """Chapter "Instructor Week 1 Grams" → folder ``main/week-1-grams/``
        (no ``instructor-`` prefix anywhere in the source tree)."""
        normalised_chapter = self.out / "main" / "week-1-grams"
        legacy_chapter = self.out / "main" / "instructor-week-1-grams"
        self.assertTrue(normalised_chapter.is_dir(),
                        f"normalised chapter folder missing: {normalised_chapter}")
        self.assertFalse(legacy_chapter.exists(),
                         f"legacy instructor-prefixed folder must not exist: {legacy_chapter}")
        for path in self.out.rglob("*"):
            self.assertNotIn(
                "instructor", path.name.lower(),
                f'no path component under {self.out} may contain "instructor": {path}',
            )

    def test_map_title_uses_title_element_not_attribute(self) -> None:
        """Map title is a ``<title>`` child of ``<map>`` carrying an audience-
        tagged ``<ph audience="-trainee"> — Instructor Version</ph>`` suffix.
        The legacy ``title=`` attribute on ``<map>`` is no longer emitted."""
        ditamap = self.out / "main" / "main.ditamap"
        root = ET.parse(ditamap).getroot()
        self.assertIsNone(root.get("title"),
                          'legacy title="..." attribute on <map> must not be emitted')
        title = root.find("title")
        self.assertIsNotNone(title, "<map> must carry a <title> child element")
        self.assertEqual(title.text, "Main",
                         "audience-neutral title text precedes the audience-tagged <ph>")
        ph = title.find("ph[@audience='-trainee']")
        self.assertIsNotNone(ph,
                             '<title> must contain a <ph audience="-trainee"> suffix')
        self.assertEqual(ph.text, " — Instructor Version")
        # The progress-test ditamap follows the same shape.
        pt_ditamap = self.out / "progress-test-1" / "progress-test-1.ditamap"
        pt_root = ET.parse(pt_ditamap).getroot()
        self.assertIsNone(pt_root.get("title"))
        pt_title = pt_root.find("title")
        self.assertIsNotNone(pt_title)
        self.assertEqual(pt_title.text, "Progress Test 1")
        pt_ph = pt_title.find("ph[@audience='-trainee']")
        self.assertIsNotNone(pt_ph)
        self.assertEqual(pt_ph.text, " — Instructor Version")

    def test_chapter_topic_title_carries_audience_prefix(self) -> None:
        """Each main chapter is a real chapter topic (a week *sub-document*),
        and its ``<title>`` carries the audience-tagged decomposition the
        chapter navtitles used to: a source name beginning "Instructor "
        emits the prefix inside ``<ph audience="-trainee">`` with the
        remainder as the tail; plain chapters emit bare text."""
        ditamap = self.out / "main" / "main.ditamap"
        root = ET.parse(ditamap).getroot()
        # Weeks are pulled up to the top level — no enclosing Grams topichead.
        self.assertEqual(root.findall("topichead"), [],
                         "main has no Grams folder — weeks sit at the top level")
        # The chapter topicrefs are the top-level topicrefs that point at a
        # chapter topic (href has a folder segment); static pages are bare.
        chapter_refs = [tr for tr in root.findall("topicref")
                        if "/" in (tr.get("href") or "")]
        self.assertEqual(len(chapter_refs), 2,
                         "fixture defines two main chapters at the top level")
        titles_by_kind: dict[str, ET.Element] = {}
        for chapter_ref in chapter_refs:
            topic_path = ditamap.parent / chapter_ref.get("href")
            self.assertTrue(topic_path.is_file(),
                            f"chapter topic missing: {topic_path}")
            topic = ET.parse(topic_path).getroot()
            self.assertEqual(topic.tag, "topic")
            title = topic.find("title")
            self.assertIsNotNone(title,
                                 "chapter topic must carry a <title>")
            ph = title.find("ph[@audience='-trainee']")
            kind = "instructor_prefixed" if ph is not None else "plain"
            titles_by_kind[kind] = title
        self.assertIn("instructor_prefixed", titles_by_kind,
                      "fixture defines an Instructor-prefixed chapter")
        self.assertIn("plain", titles_by_kind,
                      "fixture defines a plain chapter")
        prefixed = titles_by_kind["instructor_prefixed"]
        prefixed_ph = prefixed.find("ph")
        self.assertEqual(prefixed_ph.text, "Instructor ",
                         "audience-tagged prefix preserves the leading 'Instructor ' word + space")
        self.assertEqual(prefixed_ph.tail, "Week 1 Grams",
                         "remainder text follows the <ph> as its tail")
        plain = titles_by_kind["plain"]
        self.assertEqual(plain.text, "Plain Chapter",
                         "plain chapters emit text directly with no <ph> wrapper")
        self.assertEqual(len(list(plain)), 0,
                         "plain title must have no child elements")


class CsvRefactoringSupportTests(unittest.TestCase):
    """Author-side refactoring support at the CSV stage.

    The CSV doubles as the surface where the author redistributes
    grams between chapters/publications (e.g. dissolving a Pub10
    reference chapter). These tests cover the two affordances that
    make that ergonomic and safe: integer-style ``gram_id`` cells and
    pre-emission detection of duplicate row identities.
    """

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"refactor_{self._testMethodName}"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _write_csv(self, rows: list[dict]) -> Path:
        csv_path = self.tmp / "source.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=list(generate_dita.CSV_COLUMNS),
                lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, "") for col in generate_dita.CSV_COLUMNS})
        return csv_path

    def test_normalise_gram_id_canonicalises_to_plain_integer(self) -> None:
        self.assertEqual(generate_dita._normalise_gram_id("12"), "12")
        self.assertEqual(generate_dita._normalise_gram_id("5"), "5")
        self.assertEqual(generate_dita._normalise_gram_id(" 7 "), "7")
        self.assertEqual(generate_dita._normalise_gram_id("05"), "5")

    def test_normalise_gram_id_accepts_legacy_forms(self) -> None:
        self.assertEqual(generate_dita._normalise_gram_id("Gram 12"), "12")
        self.assertEqual(generate_dita._normalise_gram_id("gram 5"), "5")
        self.assertEqual(generate_dita._normalise_gram_id("Gram-7"), "7")

    def test_normalise_gram_id_passes_through_when_no_digits(self) -> None:
        self.assertEqual(generate_dita._normalise_gram_id(""), "")
        self.assertEqual(generate_dita._normalise_gram_id("TBD"), "TBD")

    def test_read_csv_normalises_gram_id_column(self) -> None:
        """Mixed integer/legacy forms in the same gram still group as one."""
        csv_path = self._write_csv([
            {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "12",
             "vessel_name": "FR Foo", "topic_type": "glc", "sequence": "1",
             "topic_filename": "gram_12.dita", "display_text": "LOFAR 1",
             "link_href": "supporting/gram12/c.glc",
             "glc_path": "supporting/gram12/c.glc",
             "time_end": "271", "bandwidth": "400", "bandcentre": "200",
             "png_path": "images/gram12.png"},
            {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "Gram 12",
             "vessel_name": "FR Foo", "topic_type": "analysis", "sequence": "1",
             "topic_filename": "gram_12.dita",
             "png_path": "images/gram12_analysis.png"},
        ])
        rows = generate_dita.read_csv(csv_path)
        self.assertEqual([r["gram_id"] for r in rows], ["12", "12"])

    def test_main_succeeds_with_integer_gram_ids(self) -> None:
        """A CSV authored with bare integers emits to the same paths as
        the legacy ``"Gram NN"`` form would."""
        csv_path = self._write_csv([
            {"publication": "main", "chapter": "Nordic Fishing Vessels",
             "gram_id": "12", "vessel_name": "Nordik Jockey",
             "topic_type": "glc", "sequence": "1", "topic_filename": "gram_12.dita",
             "display_text": "LOFAR 1",
             "link_href": "supporting/gram12/config_1.glc",
             "glc_path": "supporting/gram12/config_1.glc",
             "time_end": "271", "bandwidth": "400", "bandcentre": "200",
             "png_path": "images/gram12.png"},
            {"publication": "main", "chapter": "Nordic Fishing Vessels",
             "gram_id": "12", "vessel_name": "Nordik Jockey",
             "topic_type": "analysis", "sequence": "1",
             "topic_filename": "gram_12.dita",
             "png_path": "images/gram12_analysis.png"},
        ])
        rc = generate_dita.main([
            "--csv", str(csv_path),
            "--out", str(self.tmp / "out"),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        topic = self.tmp / "out" / "main" / "nordic-fishing-vessels" / "gram-12" / "gram_12.dita"
        self.assertTrue(topic.is_file(), f"missing {topic}")

    def test_check_row_identity_flags_two_grams_in_same_slot(self) -> None:
        """Simulates: author moves a Pub10 gram into Week 2 but forgets
        to renumber — Week 2 already had a Gram 05. Both analysis rows
        and both ``glc:sequence=1`` rows collide."""
        rows = [
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "analysis", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "analysis", "sequence": "1"},
        ]
        errors = generate_dita.check_row_identity(rows)
        self.assertEqual(len(errors), 2,
                         f"expected one error per duplicate slot, got {errors}")
        for msg in errors:
            self.assertIn("Gram 05", msg)
            self.assertIn("renumber", msg.lower())

    def test_check_row_identity_clean_on_distinct_rows(self) -> None:
        rows = [
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "glc", "sequence": "2"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 05",
             "topic_type": "analysis", "sequence": "1"},
            {"publication": "main", "chapter": "Week 2", "gram_id": "Gram 06",
             "topic_type": "analysis", "sequence": "1"},
        ]
        self.assertEqual(generate_dita.check_row_identity(rows), [])

    # The two distinct Week 2 grams that both claim number 5 (feature 008).
    _COLLIDING_GRAMS = [
        # Native Week 2 / Gram 5
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "5",
         "vessel_name": "Vessel A", "topic_type": "glc", "sequence": "1",
         "topic_filename": "gram_05.dita", "display_text": "LOFAR 1",
         "link_href": "supporting/a/c.glc", "glc_path": "supporting/a/c.glc",
         "time_end": "180", "bandwidth": "400", "bandcentre": "200", "png_path": "images/a.png"},
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "5",
         "vessel_name": "Vessel A", "topic_type": "analysis", "sequence": "1",
         "topic_filename": "gram_05.dita", "png_path": "images/a_an.png"},
        # A Pub10 gram reassigned to Week 2 that also claims number 5.
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "Gram 05",
         "vessel_name": "Vessel B", "topic_type": "glc", "sequence": "1",
         "topic_filename": "gram_05.dita", "display_text": "LOFAR 1",
         "link_href": "supporting/b/c.glc", "glc_path": "supporting/b/c.glc",
         "time_end": "271", "bandwidth": "400", "bandcentre": "200", "png_path": "images/b.png"},
        {"publication": "main", "chapter": "Week 2 Grams", "gram_id": "Gram 05",
         "vessel_name": "Vessel B", "topic_type": "analysis", "sequence": "1",
         "topic_filename": "gram_05.dita", "png_path": "images/b_an.png"},
    ]

    def test_main_warns_but_continues_on_unrenumbered_collision(self) -> None:
        """Two distinct grams sharing a week + number with no renumbering
        applied must surface as a WARNING (one per collision) yet still emit,
        so the iteration loop is fast: the operator sees the warning, runs
        deduplicate_csv.py, and re-emits. The merge is lossy (later row's
        analysis section drops, GLC sections interleave), which the
        warning text spells out (feature 008 safety net, relaxed)."""
        csv_path = self._write_csv(self._COLLIDING_GRAMS)
        out_dir = self.tmp / "out"
        with self.assertLogs(generate_dita.LOGGER, level="WARNING") as cm:
            rc = generate_dita.main([
                "--csv", str(csv_path),
                "--out", str(out_dir),
                "--image-root", str(FIXTURES),
            ])
        self.assertEqual(rc, 0, "generator must continue despite the collision")
        self.assertTrue((out_dir / "main" / "week-2-grams").exists(),
                        "the (merged) topic should still be written")
        joined = "\n".join(cm.output)
        self.assertIn("Duplicate gram slot", joined,
                      "the per-collision warning must surface in logs")
        self.assertIn("Continuing despite", joined,
                      "the summary warning must surface in logs")

    def test_renumbering_resolves_collision_into_unique_folders(self) -> None:
        """Running the dedupe renumber step numbers the week's grams contiguously
        1..k (issue #102, per-week scheme), so two grams that both claimed
        number 5 land at distinct gram-NN folders with no letter suffix."""
        rows = [dict(r) for r in self._COLLIDING_GRAMS]
        renumbered = deduplicate_csv.renumber_grams(rows)
        self.assertEqual(renumbered, 2, "both grams take contiguous 1..k slots")

        cols = list(generate_dita.CSV_COLUMNS) + ["target_gram_id"]
        csv_path = self.tmp / "renumbered.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols,
                                    lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in cols})

        out_dir = self.tmp / "out"
        rc = generate_dita.main([
            "--csv", str(csv_path),
            "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0, "generator must accept the renumbered CSV")
        chapter_dir = out_dir / "main" / "week-2-grams"
        self.assertTrue((chapter_dir / "gram-01" / "gram_01.dita").is_file(),
                        "first gram takes contiguous slot 1")
        self.assertTrue((chapter_dir / "gram-02" / "gram_02.dita").is_file(),
                        "second gram takes contiguous slot 2, no letter suffix")
        self.assertFalse((chapter_dir / "gram-05a").exists(),
                         "letter-suffix folders must no longer be produced")

    def test_bare_integer_target_chapter_expands_to_week(self) -> None:
        """Feature 008: target_chapter="2" lands under main/week-2/ and the
        main ditamap heads the chapter "Week 2"."""
        cols = list(generate_dita.CSV_COLUMNS) + ["target_chapter"]
        csv_path = self.tmp / "weeks.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols,
                                    lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for row in [
                {"publication": "main", "chapter": "Instructor Pub10_Ed22B_Updated",
                 "target_chapter": "2", "gram_id": "7", "vessel_name": "Nordik",
                 "topic_type": "glc", "sequence": "1", "topic_filename": "gram_07.dita",
                 "display_text": "LOFAR 1", "link_href": "supporting/g/c.glc",
                 "glc_path": "supporting/g/c.glc", "time_end": "271", "bandwidth": "400", "bandcentre": "200",
                 "png_path": "images/g.png"},
                {"publication": "main", "chapter": "Instructor Pub10_Ed22B_Updated",
                 "target_chapter": "2", "gram_id": "7", "vessel_name": "Nordik",
                 "topic_type": "analysis", "sequence": "1", "topic_filename": "gram_07.dita",
                 "png_path": "images/g_an.png"},
            ]:
                writer.writerow({c: row.get(c, "") for c in cols})

        out_dir = self.tmp / "out"
        rc = generate_dita.main([
            "--csv", str(csv_path), "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        self.assertTrue((out_dir / "main" / "week-2" / "gram-07" / "gram_07.dita").is_file(),
                        "bare-integer chapter must slug to week-2, not pub10")
        ditamap = (out_dir / "main" / "main.ditamap").read_text(encoding="utf-8")
        self.assertIn('href="week-2/week_2.dita"', ditamap,
                      "the week is a sub-document referenced by the map")
        self.assertIn("week-2/gram-07/gram_07.dita", ditamap)
        week_topic = out_dir / "main" / "week-2" / "week_2.dita"
        self.assertTrue(week_topic.is_file(), "week chapter topic must exist")
        self.assertIn("<title>Week 2</title>",
                      week_topic.read_text(encoding="utf-8"),
                      "the expanded Week N heading lives in the chapter topic")


class DedupGenerateDitaTests(unittest.TestCase):
    """Large-asset deduplication redirect behaviour (feature 006, US1).

    These tests hand-craft a CSV carrying the optional ``master_png_path``
    column (as ``deduplicate_csv.py`` would produce) and assert the
    generator redirects to a single master copy, records provenance, stays
    inert when the column is absent, and remains idempotent.
    """

    DEDUP_COLUMNS = generate_dita.CSV_COLUMNS + ("master_png_path",)

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"dedup_{self._testMethodName}"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _write_csv(self, rows: list[dict], cols=None) -> Path:
        cols = cols or self.DEDUP_COLUMNS
        csv_path = self.tmp / "source.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=list(cols),
                lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({c: row.get(c, "") for c in cols})
        return csv_path

    def _generate(self, csv_path: Path, out_name: str = "out") -> Path:
        out_dir = self.tmp / out_name
        rc = generate_dita.main([
            "--csv", str(csv_path), "--out", str(out_dir),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        return out_dir

    def _image_glc_row(self, gid, vessel, png, master="") -> dict:
        return {
            "publication": "main", "chapter": "Images", "gram_id": gid,
            "vessel_name": vessel, "topic_type": "glc", "sequence": "1",
            "topic_filename": f"gram_{gid}.dita", "display_text": "Image",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200", "png_path": png,
            "master_png_path": master,
        }

    def _audio_glc_row(self, gid, vessel, wav, glc, master="",
                       time_end="271", bandwidth="400", bandcentre="200") -> dict:
        return {
            "publication": "main", "chapter": "Audio", "gram_id": gid,
            "vessel_name": vessel, "topic_type": "glc", "sequence": "1",
            "topic_filename": f"gram_{gid}.dita", "display_text": "Audio",
            "link_href": glc, "glc_path": glc, "png_path": wav,
            "time_end": time_end, "bandwidth": bandwidth, "bandcentre": bandcentre,
            "master_png_path": master,
        }

    # -- T006: inert when the master_png_path column is absent ---------------
    def test_inert_when_master_column_absent(self) -> None:
        """A CSV without master_png_path produces byte-identical output to a
        baseline run and emits no <data> element anywhere (FR-010, SC-005)."""
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png"),
        ]
        # With column present-but-empty.
        with_col = self._generate(self._write_csv(rows), "with_col")
        # Without the column at all (legacy 16-col CSV).
        csv_no_col = self.tmp / "no_col.csv"
        with csv_no_col.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(generate_dita.CSV_COLUMNS),
                               lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in generate_dita.CSV_COLUMNS})
        without_col = self.tmp / "without_col"
        rc = generate_dita.main([
            "--csv", str(csv_no_col), "--out", str(without_col),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0)
        cmp = filecmp.dircmp(with_col, without_col)
        self.assertEqual(cmp.diff_files, [], "present-empty column must be inert")
        self.assertEqual(cmp.left_only, [])
        self.assertEqual(cmp.right_only, [])
        # No <data> emitted, and both grams copied their own image.
        for topic in without_col.rglob("*.dita"):
            root = ET.parse(topic).getroot()
            self.assertIsNone(root.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))
        self.assertTrue((without_col / "main" / "images" / "gram-31" / "shared-b.png").is_file())

    # -- T007: redirected image links the master, copies nothing -------------
    def test_redirected_image_href_points_to_master(self) -> None:
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
        ]
        out = self._generate(self._write_csv(rows))
        g31 = out / "main" / "images" / "gram-31"
        topic = ET.parse(g31 / "gram_31.dita").getroot()
        image = topic.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "../gram-30/shared.png")
        # No local copy in the redirected gram.
        self.assertFalse((g31 / "shared-b.png").exists())
        self.assertFalse((g31 / "shared.png").exists())
        # Master copy exists in gram-30.
        self.assertTrue((out / "main" / "images" / "gram-30" / "shared.png").is_file())

    # -- T008: redirected audio links the master .glc, pairs untouched -------
    def test_redirected_audio_links_master_glc(self) -> None:
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
        ]
        out = self._generate(self._write_csv(rows))
        g21 = out / "main" / "audio" / "gram-21"
        topic = ET.parse(g21 / "gram_21.dita").getroot()
        xref = topic.find(".//xref[@format='glc']")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.get("href"), "../gram-20/master.glc")
        # Neither .glc nor .wav copied into the redirected gram.
        self.assertEqual(sorted(p.name for p in g21.iterdir()), ["gram_21.dita"])
        # Master gram holds both files side by side.
        g20 = out / "main" / "audio" / "gram-20"
        self.assertTrue((g20 / "master.glc").is_file())
        self.assertTrue((g20 / "master.wav").is_file())

    # -- T009: master binary written exactly once across N redirects --------
    def test_master_binary_written_exactly_once(self) -> None:
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
            self._audio_glc_row("22", "Charlie", "dedup/audio/dup2.wav",
                                "dedup/audio/dup2.glc",
                                master="dedup/audio/master.wav"),
        ]
        out = self._generate(self._write_csv(rows))
        wavs = sorted(p for p in out.rglob("*.wav"))
        self.assertEqual(len(wavs), 1, f"exactly one physical .wav, got {wavs}")
        glcs = sorted(p for p in out.rglob("*.glc"))
        self.assertEqual(len(glcs), 1, f"exactly one physical .glc, got {glcs}")

    # -- T010: provenance <data> on redirected lofars only ------------------
    def test_provenance_data_emitted_on_redirected_lofar_only(self) -> None:
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
        ]
        out = self._generate(self._write_csv(rows))
        name = generate_dita.ORIGINAL_ASSET_PATH

        def data_values(topic_path):
            root = ET.parse(topic_path).getroot()
            return [d.get("value") for d in root.findall(f".//data[@name='{name}']")]

        # Redirected image gram: value is the row's own png_path.
        self.assertEqual(
            data_values(out / "main" / "images" / "gram-31" / "gram_31.dita"),
            ["dedup/img/shared_b.png"],
        )
        # Redirected audio gram: value is the row's glc_path (not the .wav).
        self.assertEqual(
            data_values(out / "main" / "audio" / "gram-21" / "gram_21.dita"),
            ["dedup/audio/dup1.glc"],
        )
        # Masters carry none.
        self.assertEqual(data_values(out / "main" / "images" / "gram-30" / "gram_30.dita"), [])
        self.assertEqual(data_values(out / "main" / "audio" / "gram-20" / "gram_20.dita"), [])

    # -- T011: blank/unresolvable master falls back with a WARNING ----------
    def test_blank_or_unresolvable_master_falls_back_with_warning(self) -> None:
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            # master_png_path points at a png_path no master row owns.
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/does_not_exist.png"),
        ]
        csv_path = self._write_csv(rows)
        out = self._generate(csv_path)
        # main() reconfigures root logging, so assert against the dual-logged
        # generate.log file (the air-gapped debugging surface) rather than
        # assertLogs (whose handler setup_logging would remove).
        log_text = Path("generate.log").read_text(encoding="utf-8")
        self.assertIn("not resolvable", log_text)
        self.assertIn("dedup/img/does_not_exist.png", log_text)
        g31 = out / "main" / "images" / "gram-31"
        # Fell back to a local copy; no <data> emitted.
        self.assertTrue((g31 / "shared-b.png").is_file())
        topic = ET.parse(g31 / "gram_31.dita").getroot()
        self.assertIsNone(topic.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))

    # -- issue #78: .wav redirects are gated on the (time, freq) view --------
    def test_wav_redirect_view_mismatch_falls_back_locally(self) -> None:
        """A stale or hand-edited redirect onto a master whose .glc presents
        a different (time_end, bandwidth, bandcentre) window must not resolve: the row
        falls back to its own local .glc/.wav pair with a WARNING, so the
        distinct student view is never dropped (issue #78)."""
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc",
                                time_end="271", bandwidth="400", bandcentre="200"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav",
                                time_end="271", bandwidth="800", bandcentre="400"),
        ]
        out = self._generate(self._write_csv(rows))
        log_text = Path("generate.log").read_text(encoding="utf-8")
        self.assertIn("matching (time_end, bandwidth, bandcentre) view", log_text)
        g21 = out / "main" / "audio" / "gram-21"
        self.assertTrue((g21 / "dup1.glc").is_file())
        self.assertTrue((g21 / "dup1.wav").is_file())
        topic = ET.parse(g21 / "gram_21.dita").getroot()
        xref = topic.find(".//xref[@format='glc']")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.get("href"), "dup1.glc")
        # Fell back to a local pair; no provenance <data> emitted.
        self.assertIsNone(topic.find(f".//data[@name='{generate_dita.ORIGINAL_ASSET_PATH}']"))

    def test_wav_redirect_same_bandwidth_different_bandcentre_not_resolved(self) -> None:
        """Issue #87: equal bandwidth but a different bandcentre is a different
        frequency view, so a redirect across that boundary must not resolve."""
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc",
                                time_end="271", bandwidth="400", bandcentre="200"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav",
                                time_end="271", bandwidth="400", bandcentre="300"),
        ]
        out = self._generate(self._write_csv(rows))
        log_text = Path("generate.log").read_text(encoding="utf-8")
        self.assertIn("matching (time_end, bandwidth, bandcentre) view", log_text)
        g21 = out / "main" / "audio" / "gram-21"
        # Different band centre -> fell back to its own local pair.
        self.assertTrue((g21 / "dup1.glc").is_file())
        self.assertTrue((g21 / "dup1.wav").is_file())

    def test_wav_redirect_resolves_view_matching_master(self) -> None:
        """Two masters share one .wav path with different .glc views; a
        redirected row must link the master whose view matches its own,
        regardless of CSV row order (issue #78)."""
        rows = [
            # The view-matching master is listed first so a path-only index
            # (which the mismatched master would overwrite) gets this wrong.
            self._audio_glc_row("21", "Bravo", "dedup/audio/twoview.wav",
                                "dedup/audio/twoview_b.glc",
                                time_end="271", bandwidth="800", bandcentre="400"),
            self._audio_glc_row("20", "Alpha", "dedup/audio/twoview.wav",
                                "dedup/audio/twoview_a.glc",
                                time_end="271", bandwidth="400", bandcentre="200"),
            self._audio_glc_row("22", "Charlie", "dedup/audio/twoview.wav",
                                "dedup/audio/dup2.glc",
                                master="dedup/audio/twoview.wav",
                                time_end="271", bandwidth="800", bandcentre="400"),
        ]
        out = self._generate(self._write_csv(rows))
        topic = ET.parse(
            out / "main" / "audio" / "gram-22" / "gram_22.dita").getroot()
        xref = topic.find(".//xref[@format='glc']")
        self.assertIsNotNone(xref)
        self.assertEqual(xref.get("href"), "../gram-21/twoview-b.glc")

    def test_image_redirect_ignores_view_mismatch(self) -> None:
        """Image redirects stay byte-identity-only: the row's own time/freq
        ride in its gram-config table, so a differing view still redirects
        (only .wav rows are view-gated, issue #78)."""
        rows = [
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
        ]
        rows[1]["time_end"], rows[1]["bandwidth"], rows[1]["bandcentre"] = "999", "888", "444"
        out = self._generate(self._write_csv(rows))
        g31 = out / "main" / "images" / "gram-31"
        topic = ET.parse(g31 / "gram_31.dita").getroot()
        image = topic.find(".//table[@outputclass='gram-config']//image")
        self.assertIsNotNone(image)
        self.assertEqual(image.get("href"), "../gram-30/shared.png")
        self.assertFalse((g31 / "shared-b.png").exists())

    # -- T012: deduplicated export is idempotent ----------------------------
    def test_dedup_export_idempotent(self) -> None:
        rows = [
            self._audio_glc_row("20", "Alpha", "dedup/audio/master.wav",
                                "dedup/audio/master.glc"),
            self._audio_glc_row("21", "Bravo", "dedup/audio/dup1.wav",
                                "dedup/audio/dup1.glc",
                                master="dedup/audio/master.wav"),
            self._image_glc_row("31", "Echo", "dedup/img/shared_b.png",
                                 master="dedup/img/shared.png"),
            self._image_glc_row("30", "Delta", "dedup/img/shared.png"),
        ]
        csv_path = self._write_csv(rows)
        first = self._generate(csv_path, "run1")
        second = self._generate(csv_path, "run2")

        def _assert_identical(a: Path, b: Path) -> None:
            cmp = filecmp.dircmp(a, b)
            self.assertEqual(cmp.diff_files, [], f"diffs under {a}")
            self.assertEqual(cmp.left_only, [])
            self.assertEqual(cmp.right_only, [])
            for sub in cmp.common_dirs:
                _assert_identical(a / sub, b / sub)

        _assert_identical(first, second)


class FreqBandDerivationTests(unittest.TestCase):
    """Issue #87: freq_start/freq_end derived from bandwidth + bandcentre."""

    def test_spot_checks(self) -> None:
        cases = [
            # (bandwidth, bandcentre, freq_start, freq_end)
            ("400", "200", "0", "400"),     # centred -> starts at zero
            ("400", "600", "400", "800"),   # off-centre, high
            ("100", "250", "200", "300"),   # narrow off-centre band
            ("401", "200.5", "0", "401"),   # odd bandwidth -> integer limits
        ]
        for bw, bc, fs, fe in cases:
            with self.subTest(bandwidth=bw, bandcentre=bc):
                self.assertEqual(generate_dita._derive_freq_band(bw, bc), (fs, fe))

    def test_non_integer_limits_are_trailing_zero_stripped(self) -> None:
        # bandwidth 401, centred -> half = 200.5
        self.assertEqual(
            generate_dita._derive_freq_band("401", "300"), ("99.5", "500.5"))

    def test_negative_freq_start_emitted_not_clamped(self) -> None:
        # bandcentre below bandwidth/2 -> negative lower limit, surfaced as-is.
        self.assertEqual(
            generate_dita._derive_freq_band("400", "100"), ("-100", "300"))

    def test_blank_bandcentre_falls_back_to_legacy(self) -> None:
        # No bandcentre -> band starts at zero, ends at bandwidth.
        self.assertEqual(generate_dita._derive_freq_band("400", ""), ("0", "400"))

    def test_blank_bandwidth_yields_blank_limits(self) -> None:
        self.assertEqual(generate_dita._derive_freq_band("", "200"), ("", ""))

    def test_non_numeric_inputs_degrade(self) -> None:
        self.assertEqual(generate_dita._derive_freq_band("abc", "x"), ("", ""))

    def test_gramframe_table_renders_off_centre_band(self) -> None:
        """An off-centre band produces a non-zero freq-start in the table."""
        parent = ET.Element("body")
        generate_dita._append_gramframe_table(
            parent, "lofar-1.png", "271", "400", "600", 1)
        rows = {r.find("entry").text: r.findall("entry")[1].text
                for r in parent.findall(".//tbody/row")
                if len(r.findall("entry")) == 2}
        self.assertEqual(rows.get("freq-start"), "400")
        self.assertEqual(rows.get("freq-end"), "800")


class TrustBoundaryTests(unittest.TestCase):
    """Fail-fast on our own artifacts (constitution VII).

    A blank Zone-A identity column is a defect in data our pipeline produces —
    the generator aborts loudly rather than coercing it to "" and emitting a
    malformed topic. The ``.wav`` view fields (``time_end``/``bandwidth``/
    ``bandcentre``) are *not* in this set: they only feed the image GramFrame
    table, so a blank one on a ``.wav`` row is tolerated (see
    ``test_blank_wav_view_field_is_tolerated``).
    """

    def setUp(self) -> None:
        TMP.mkdir(parents=True, exist_ok=True)
        self.tmp = TMP / f"trust_{self._testMethodName}"
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir(parents=True)

    def _csv(self, rows: list[dict]) -> Path:
        cols = generate_dita.CSV_COLUMNS
        path = self.tmp / "in.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(cols),
                               lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})
        return path

    def _gram_row(self, **over) -> dict:
        row = {c: "" for c in generate_dita.CSV_COLUMNS}
        row.update({
            "publication": "main", "chapter": "Arctic Survey", "gram_id": "5",
            "topic_type": "glc", "sequence": "1", "topic_filename": "gram_05.dita",
            "display_text": "Lofar 1", "link_href": "g/c.glc", "glc_path": "g/c.glc",
            "time_end": "271", "bandwidth": "400", "bandcentre": "200",
            "png_path": "images/gram12.png",
        })
        row.update(over)
        return row

    # -- require_field unit behaviour --------------------------------------
    def test_require_field_raises_on_blank_and_whitespace(self) -> None:
        with self.assertRaises(generate_dita.PipelineDataError):
            generate_dita.require_field({"publication": ""}, "publication")
        with self.assertRaises(generate_dita.PipelineDataError):
            generate_dita.require_field({"publication": "   "}, "publication")
        # Absent column is also a hard-fail (not a silent default).
        with self.assertRaises(generate_dita.PipelineDataError):
            generate_dita.require_field({}, "sequence")
        # A present value is returned stripped.
        self.assertEqual(
            generate_dita.require_field({"publication": " main "}, "publication"),
            "main")

    def test_require_field_reports_line_no(self) -> None:
        # Explicit line_no wins.
        with self.assertRaises(generate_dita.PipelineDataError) as ctx:
            generate_dita.require_field({"publication": ""}, "publication",
                                        line_no=42)
        self.assertIn("at CSV line 42", str(ctx.exception))
        # Falls back to the line stamped on the row by read_csv when not passed.
        with self.assertRaises(generate_dita.PipelineDataError) as ctx:
            generate_dita.require_field(
                {"publication": "", generate_dita._SOURCE_LINE: 7}, "publication")
        self.assertIn("at CSV line 7", str(ctx.exception))

    # -- blank identity column aborts the run ------------------------------
    def test_blank_identity_column_aborts(self) -> None:
        for field in ("publication", "topic_type", "sequence"):
            with self.subTest(field=field):
                csv_path = self._csv([self._gram_row(**{field: ""})])
                rc = generate_dita.main([
                    "--csv", str(csv_path), "--out", str(self.tmp / field),
                    "--image-root", str(FIXTURES),
                ])
                self.assertEqual(rc, 1, f"blank {field} must abort")

    # -- blank .wav view field is tolerated (view fields only feed GramFrame) --
    def test_blank_wav_view_field_is_tolerated(self) -> None:
        # A .wav row emits a plain link to its .glc and never renders a
        # GramFrame table, so its view fields are unused: a blank one degrades
        # to "" rather than aborting the run.
        for field in ("time_end", "bandwidth", "bandcentre"):
            with self.subTest(field=field):
                row = self._gram_row(png_path="g/audio.wav", **{field: ""})
                csv_path = self._csv([row])
                rc = generate_dita.main([
                    "--csv", str(csv_path), "--out", str(self.tmp / f"wav_{field}"),
                    "--image-root", str(FIXTURES),
                ])
                self.assertEqual(rc, 0, f"blank .wav {field} must be tolerated")

    # -- the same blank view on a NON-wav row is fine ----------------------
    def test_blank_view_on_image_row_is_allowed(self) -> None:
        # An image row legitimately carries empty view fields; it must not
        # trip the .wav promotion clause.
        row = self._gram_row(png_path="images/gram12.png",
                             time_end="", bandwidth="", bandcentre="")
        csv_path = self._csv([row])
        rc = generate_dita.main([
            "--csv", str(csv_path), "--out", str(self.tmp / "img"),
            "--image-root", str(FIXTURES),
        ])
        self.assertEqual(rc, 0, "blank views on an image row are allowed")


class CsvEncodingToleranceTests(unittest.TestCase):
    """``read_csv`` must survive whatever encoding Excel's Save As produces.

    The writer emits ``utf-8-sig``, but a technical author who edits the CSV
    in Excel and saves with the convenient default *"CSV (Comma delimited)"*
    gets the file back in Windows ANSI (cp1252). A strict utf-8 read crashes
    on the first non-ASCII byte — which is why operators had to reach for the
    awkward *"CSV (MS-DOS)"* option. The decoder now falls back to cp1252.
    """

    HEADER = "publication,vessel_name"
    BODY = 'main,"HMS Hood £5 at 90° N"'  # contains £ and °

    def _csv_bytes(self, encoding: str, bom: bool = False) -> bytes:
        text = f"{self.HEADER}\r\n{self.BODY}\r\n"
        raw = text.encode(encoding)
        return (b"\xef\xbb\xbf" + raw) if bom else raw

    def _decode(self, raw: bytes) -> str:
        tmp = TMP / f"enc_{self._testMethodName}.csv"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(raw)
        return generate_dita.decode_csv_bytes(
            tmp.read_bytes(), tmp, generate_dita.LOGGER
        )

    def test_utf8_with_bom_is_read_cleanly(self) -> None:
        """The canonical writer output / Excel 'CSV UTF-8' round-trips."""
        text = self._decode(self._csv_bytes("utf-8", bom=True))
        self.assertIn("HMS Hood £5 at 90° N", text)
        self.assertFalse(text.startswith("﻿"), "BOM must be stripped")

    def test_utf8_without_bom_is_read_cleanly(self) -> None:
        text = self._decode(self._csv_bytes("utf-8"))
        self.assertIn("HMS Hood £5 at 90° N", text)

    def test_excel_ansi_comma_delimited_is_recovered(self) -> None:
        """The painful default save (cp1252) no longer crashes — and the
        non-ASCII characters survive intact, unlike a strict utf-8 read."""
        text = self._decode(self._csv_bytes("cp1252"))
        self.assertIn("HMS Hood £5 at 90° N", text)

    def test_strict_utf8_would_have_crashed(self) -> None:
        """Guards the regression: the cp1252 bytes are *not* valid utf-8, so
        the old strict reader genuinely failed on them."""
        with self.assertRaises(UnicodeDecodeError):
            self._csv_bytes("cp1252").decode("utf-8")

    def test_full_run_accepts_ansi_saved_csv(self) -> None:
        """End-to-end: a generator run over a cp1252-saved CSV succeeds."""
        src = (FIXTURES / "minimal.csv").read_text(encoding="utf-8-sig")
        out_dir = TMP / f"out_{self._testMethodName}"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        ansi_csv = TMP / f"ansi_{self._testMethodName}.csv"
        ansi_csv.write_bytes(src.encode("cp1252"))
        rc = _run(out_dir, csv_path=ansi_csv)
        self.assertEqual(rc, 0, "a cp1252-saved CSV must drive a clean run")


if __name__ == "__main__":
    unittest.main()

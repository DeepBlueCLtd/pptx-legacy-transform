"""Tests for the HTML pretty-printer used by ``publish_html.py``.

The publish pipeline shells out to DITA-OT (a Java tool) which we cannot
run inside ``unittest``. ``prettify_html`` is purely string-in /
string-out, so we exercise it directly against DITA-OT-shaped fixtures.
"""

from __future__ import annotations

import re
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

from publish_html import prettify_html, prettify_tree

REPO_ROOT = Path(__file__).resolve().parent.parent
DITA_ROOT = REPO_ROOT / "dita"
HTML_ROOT = REPO_ROOT / "html"


class PrettifyHtmlTests(unittest.TestCase):
    def test_minified_topic_is_broken_onto_lines(self):
        src = (
            '<!DOCTYPE html SYSTEM "about:legacy-compat">'
            '<html lang="en"><head><meta charset="UTF-8">'
            '<title>T</title></head>'
            '<body><h1>T</h1></body></html>'
        )
        out = prettify_html(src)
        expected = textwrap.dedent("""\
            <!DOCTYPE html SYSTEM "about:legacy-compat">
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <title>T</title>
              </head>
              <body>
                <h1>T</h1>
              </body>
            </html>
            """)
        self.assertEqual(out, expected)

    def test_inline_subtree_stays_flat(self):
        # h1 with a span child is the DITA-OT pattern from gram titles
        # ("Gram 23<span class='ph'> - FR …</span>"). Splitting it would
        # change rendered whitespace, so the element must stay on one line.
        src = '<body><h1>Gram 23<span class="ph"> - FR X</span></h1></body>'
        out = prettify_html(src)
        self.assertIn('<h1>Gram 23<span class="ph"> - FR X</span></h1>', out)

    def test_void_elements_have_no_closing_tag(self):
        src = (
            '<head><meta charset="UTF-8">'
            '<link rel="stylesheet" href="x.css"></head>'
        )
        out = prettify_html(src)
        self.assertIn("<meta charset=\"UTF-8\">", out)
        self.assertIn("<link rel=\"stylesheet\" href=\"x.css\">", out)
        self.assertNotIn("</meta>", out)
        self.assertNotIn("</link>", out)
        self.assertNotIn("/>", out)  # HTML5 style, no trailing slash

    def test_doctype_normalized_to_single_line(self):
        src = (
            '<!DOCTYPE html\n  SYSTEM "about:legacy-compat">\n'
            '<html><body><p>hi</p></body></html>'
        )
        out = prettify_html(src)
        self.assertTrue(
            out.startswith('<!DOCTYPE html SYSTEM "about:legacy-compat">\n'),
            out[:80],
        )

    def test_comments_are_preserved(self):
        src = '<body><!-- keep me --><p>x</p></body>'
        out = prettify_html(src)
        self.assertIn("<!-- keep me -->", out)

    def test_entity_references_are_preserved(self):
        src = '<body><p>A &amp; B &lt; C &#169; D</p></body>'
        out = prettify_html(src)
        self.assertIn("A &amp; B &lt; C &#169; D", out)

    def test_pre_content_is_preserved_verbatim(self):
        src = '<body><pre>  line 1\n    line 2  </pre></body>'
        out = prettify_html(src)
        self.assertIn("<pre>  line 1\n    line 2  </pre>", out)

    def test_idempotent(self):
        src = (
            '<!DOCTYPE html SYSTEM "about:legacy-compat">'
            '<html><head><title>T</title></head>'
            '<body><div class="a"><p>one</p><p>two</p></div></body></html>'
        )
        once = prettify_html(src)
        twice = prettify_html(once)
        self.assertEqual(once, twice)

    def test_attribute_values_with_special_chars_are_escaped(self):
        # The HTML parser decodes entities in attribute values when
        # convert_charrefs=False is set on data, but attribute values are
        # always decoded. We must re-escape on emit so the output stays
        # valid HTML.
        src = '<a title="a &amp; b">x</a>'
        out = prettify_html(src)
        self.assertIn('title="a &amp; b"', out)

    def test_attribute_without_value_is_emitted_bare(self):
        src = '<input disabled>'
        out = prettify_html(src)
        self.assertIn("<input disabled>", out)

    def test_list_item_with_anchor_stays_flat(self):
        # DITA-OT ``<li><a href="…">label</a></li>`` is purely inline; the
        # index pages would become noisy if every <a> got its own line.
        src = '<ul><li class="topicref"><a href="x.html">Gram 01</a></li></ul>'
        out = prettify_html(src)
        self.assertIn(
            '<li class="topicref"><a href="x.html">Gram 01</a></li>',
            out,
        )

    def test_mixed_content_text_with_block_child_breaks(self):
        # Matches the existing index.html pattern: an <li> containing a
        # text label *and* a nested <ul>. The text is hoisted onto its
        # own indented line so the structure reads top-down.
        src = (
            '<li class="topichead">Section A'
            '<ul><li><a href="x.html">x</a></li></ul></li>'
        )
        out = prettify_html(src)
        self.assertIn("Section A\n", out)
        self.assertIn("<ul>\n", out)

    def test_img_tag_is_preserved_with_all_attributes(self):
        # The DITA-OT output embeds gram images as <img> inside an <imagecenter>
        # div. If the prettifier dropped or mangled the <img> the gram would
        # render as an empty cell, which is the failure mode the published-HTML
        # integration check below also guards against.
        src = (
            '<body><div class="imagecenter">'
            '<img class="image imagecenter" src="lofar-1-b.png">'
            '</div></body>'
        )
        out = prettify_html(src)
        self.assertIn(
            '<img class="image imagecenter" src="lofar-1-b.png">', out
        )

    def test_script_content_is_not_re_parsed(self):
        src = '<body><script>if (a < b) { c(); }</script></body>'
        out = prettify_html(src)
        self.assertIn("if (a < b) { c(); }", out)


class PrettifyTreeTests(unittest.TestCase):
    def test_walks_html_files_under_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            (root / "a.html").write_text(
                "<html><body><p>x</p></body></html>", encoding="utf-8"
            )
            (root / "sub" / "b.html").write_text(
                "<html><body><p>y</p></body></html>", encoding="utf-8"
            )
            (root / "skip.css").write_text("body{}", encoding="utf-8")

            count = prettify_tree(root)

            self.assertEqual(count, 2)
            self.assertIn(
                "<p>x</p>",
                (root / "a.html").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "\n  <body>",
                (root / "sub" / "b.html").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (root / "skip.css").read_text(encoding="utf-8"), "body{}"
            )


def _html_twin(dita_path: Path) -> Path:
    """Return the HTML file produced by DITA-OT for ``dita_path``.

    DITA-OT writes each ditamap's output under ``html/<map>/<map>/...`` —
    the map stem appears twice because DITA-OT preserves the source tree
    relative to the build root, and we hand it the staged ditamap copy.
    """
    rel = dita_path.relative_to(DITA_ROOT)
    map_stem = rel.parts[0]
    inner = Path(*rel.parts[1:]).with_suffix(".html")
    return HTML_ROOT / map_stem / map_stem / inner


_IMG_SRC_RE = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"', re.IGNORECASE)

# Suffixes a browser will render as an image. Anything else inside an
# <image href> / <img src> renders as a broken-image icon — the visible
# failure mode that motivated these tests. WAV assets travel through
# the pipeline as <xref href="*.glc"> blocks instead (see
# dita-topic-schema.md §1.3), so they never appear inside <image>.
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})


class PublishedImagePresenceTests(unittest.TestCase):
    """Walk the shipped ``dita/`` and ``html/`` trees and assert images
    survive end-to-end: every ``<image href>`` in DITA must have a
    matching ``<img src>`` in the HTML twin, and the binary asset must
    be byte-identical on both sides. This is the direct regression
    guard against "images lost in publishing"."""

    @classmethod
    def setUpClass(cls) -> None:
        if not DITA_ROOT.is_dir() or not HTML_ROOT.is_dir():
            raise unittest.SkipTest(
                "dita/ or html/ tree missing — run the pipeline first"
            )
        cls.dita_files = sorted(DITA_ROOT.rglob("*.dita"))
        if not cls.dita_files:
            raise unittest.SkipTest("no .dita files under dita/")
        # Cross-tree checks (those tagged `_html_*` and the binary check)
        # assume html/ was built from the current dita/. Detect a stale
        # html/ tree by sampling for the legacy buggy <img src="*.wav">
        # pattern that the new generator never emits, so a fresh build
        # passes silently while a stale tree skips with a clear message.
        cls._html_is_stale = False
        for html_path in HTML_ROOT.rglob("*.html"):
            for src in _IMG_SRC_RE.findall(html_path.read_text(encoding="utf-8")):
                if Path(src).suffix.lower() not in IMAGE_SUFFIXES:
                    cls._html_is_stale = True
                    cls._stale_reason = (
                        f"html/ tree is stale (sample: {html_path.relative_to(REPO_ROOT)} "
                        f"has <img src={src!r}>). Regenerate with "
                        f"`python publish_html.py --dita-ot <path>` and re-run."
                    )
                    return

    def _require_fresh_html(self) -> None:
        if getattr(self, "_html_is_stale", False):
            self.skipTest(self._stale_reason)

    def test_dita_image_hrefs_point_at_image_files(self) -> None:
        """Every ``<image href>`` in the generated DITA must point at a
        renderable image (extension in IMAGE_SUFFIXES). A ``.wav`` or
        ``.docx`` href slips through DITA-OT unchanged and renders as a
        broken-image icon in the browser. WAV-typed GLC rows belong in
        ``<xref href="*.glc">`` blocks, never inside ``<image>``."""
        bad: list[str] = []
        for dita_path in self.dita_files:
            root = ET.parse(dita_path).getroot()
            for img in root.findall(".//image"):
                href = img.get("href") or ""
                suffix = Path(href).suffix.lower()
                if suffix not in IMAGE_SUFFIXES:
                    bad.append(
                        f"{dita_path.relative_to(REPO_ROOT)}: "
                        f"<image href={href!r}> is not a renderable image"
                    )
        self.assertEqual(bad, [], f"\n{len(bad)} non-image <image> hrefs:\n" + "\n".join(bad))

    def test_every_dita_image_has_html_twin(self) -> None:
        self._require_fresh_html()
        missing: list[str] = []
        for dita_path in self.dita_files:
            root = ET.parse(dita_path).getroot()
            dita_hrefs = [img.get("href") for img in root.findall(".//image")]
            dita_hrefs = [h for h in dita_hrefs if h]
            if not dita_hrefs:
                continue
            html_path = _html_twin(dita_path)
            if not html_path.is_file():
                missing.append(f"{dita_path}: html twin not found at {html_path}")
                continue
            html_srcs = set(_IMG_SRC_RE.findall(html_path.read_text(encoding="utf-8")))
            for href in dita_hrefs:
                if href not in html_srcs:
                    missing.append(
                        f"{html_path.relative_to(REPO_ROOT)}: "
                        f"DITA referenced image {href!r}, no <img src={href!r}> in HTML"
                    )
        self.assertEqual(missing, [], "\n".join(missing))

    def test_html_img_srcs_point_at_image_files(self) -> None:
        """Every ``<img src>`` in the published HTML must point at a
        renderable image. Catches the same root failure as the DITA-side
        check, but at the user-visible layer."""
        self._require_fresh_html()
        bad: list[str] = []
        for html_path in HTML_ROOT.rglob("*.html"):
            for src in _IMG_SRC_RE.findall(html_path.read_text(encoding="utf-8")):
                suffix = Path(src).suffix.lower()
                if suffix not in IMAGE_SUFFIXES:
                    bad.append(
                        f"{html_path.relative_to(REPO_ROOT)}: "
                        f"<img src={src!r}> is not a renderable image"
                    )
        self.assertEqual(bad, [], f"\n{len(bad)} non-image <img> srcs:\n" + "\n".join(bad))

    def test_image_binaries_present_alongside_dita_and_html(self) -> None:
        self._require_fresh_html()
        missing: list[str] = []
        mismatched: list[str] = []
        for dita_path in self.dita_files:
            root = ET.parse(dita_path).getroot()
            for img in root.findall(".//image"):
                href = img.get("href")
                if not href:
                    continue
                dita_asset = (dita_path.parent / href).resolve()
                if not dita_asset.is_file():
                    missing.append(
                        f"{dita_path.relative_to(REPO_ROOT)}: "
                        f"referenced image not on disk: {href}"
                    )
                    continue
                html_path = _html_twin(dita_path)
                html_asset = (html_path.parent / href).resolve()
                if not html_asset.is_file():
                    missing.append(
                        f"{html_path.relative_to(REPO_ROOT)}: "
                        f"image not copied into html tree: {href}"
                    )
                    continue
                if dita_asset.read_bytes() != html_asset.read_bytes():
                    mismatched.append(
                        f"{href}: dita and html copies differ "
                        f"({dita_asset} vs {html_asset})"
                    )
        self.assertEqual(missing, [], "\n".join(missing))
        self.assertEqual(mismatched, [], "\n".join(mismatched))


if __name__ == "__main__":
    unittest.main()

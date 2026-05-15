"""Tests for the HTML pretty-printer used by ``publish_html.py``.

The publish pipeline shells out to DITA-OT (a Java tool) which we cannot
run inside ``unittest``. ``prettify_html`` is purely string-in /
string-out, so we exercise it directly against DITA-OT-shaped fixtures.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from publish_html import prettify_html, prettify_tree


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


if __name__ == "__main__":
    unittest.main()

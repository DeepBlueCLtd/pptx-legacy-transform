"""Tests for the HTML pretty-printer used by ``publish_html.py``.

The publish pipeline shells out to DITA-OT (a Java tool) which we cannot
run inside ``unittest``. ``prettify_html`` is purely string-in /
string-out, so we exercise it directly against DITA-OT-shaped fixtures.
"""

from __future__ import annotations

import os
import re
import textwrap
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import publish_html
from publish_html import (
    EDITIONS,
    Edition,
    GRAMFRAME_BUNDLE_NAME,
    THEME_BUNDLE_NAME,
    _dita_ot_command,
    inject_gramframe_plugin,
    inject_operator_console_theme,
    prettify_html,
    prettify_tree,
    publish,
    scrub_nondeterministic_metadata,
    write_edition_index,
    write_shared_landing,
)

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

    def test_walks_both_edition_subtrees(self):
        """Spec 003: the publisher writes html/instructor/ and html/student/.
        A single prettify_tree(html/) call must walk both."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "instructor" / "main").mkdir(parents=True)
            (root / "student" / "main").mkdir(parents=True)
            (root / "instructor" / "main" / "a.html").write_text(
                "<html><body><p>i</p></body></html>", encoding="utf-8",
            )
            (root / "student" / "main" / "b.html").write_text(
                "<html><body><p>s</p></body></html>", encoding="utf-8",
            )
            self.assertEqual(prettify_tree(root), 2)


# -----------------------------------------------------------------------------
# Spec 003 — Editions and DITA-OT invocation contract
# -----------------------------------------------------------------------------

class EditionsTests(unittest.TestCase):
    """Spec 003 — two editions, in instructor-then-student order."""

    def test_editions_are_instructor_then_student(self):
        self.assertEqual([e.name for e in EDITIONS], ["instructor", "student"])

    def test_instructor_edition_has_no_filter(self):
        instructor = next(e for e in EDITIONS if e.name == "instructor")
        self.assertIsNone(instructor.ditaval)
        self.assertEqual(instructor.output_subdir, "instructor")

    def test_student_edition_uses_trainee_ditaval(self):
        student = next(e for e in EDITIONS if e.name == "student")
        self.assertEqual(student.ditaval, Path("trainee.ditaval"))
        self.assertEqual(student.output_subdir, "student")

    def test_each_edition_has_a_human_description(self):
        for edition in EDITIONS:
            self.assertGreaterEqual(
                len(edition.description), 20,
                f"{edition.name} edition needs a >=20-char audience description",
            )


class DitaOtCommandTests(unittest.TestCase):
    """``_dita_ot_command`` builds the argv the publisher hands to subprocess."""

    def test_instructor_command_omits_filter_flag(self):
        argv = _dita_ot_command(
            dita_ot=Path("/opt/dita-ot"),
            ditamap=Path("/staged/main.ditamap"),
            target=Path("/html/instructor/main"),
            ditaval=None,
        )
        self.assertIn("--input=/staged/main.ditamap", argv)
        self.assertIn("--output=/html/instructor/main", argv)
        self.assertIn("--format=html5", argv)
        self.assertFalse(
            any(arg.startswith("--filter=") for arg in argv),
            "instructor edition must NOT pass --filter",
        )

    def test_student_command_includes_filter_flag(self):
        argv = _dita_ot_command(
            dita_ot=Path("/opt/dita-ot"),
            ditamap=Path("/staged/main.ditamap"),
            target=Path("/html/student/main"),
            ditaval=Path("/staged/trainee.ditaval"),
        )
        self.assertIn("--filter=/staged/trainee.ditaval", argv)
        self.assertIn("--output=/html/student/main", argv)


class PublishDualEditionTests(unittest.TestCase):
    """``publish()`` runs DITA-OT twice per ditamap — once per edition."""

    def _make_staged(self, tmp: Path) -> Path:
        staged = tmp / ".dita-build"
        staged.mkdir()
        (staged / "main.ditamap").write_text("<map/>", encoding="utf-8")
        (staged / "progress-test-1.ditamap").write_text("<map/>", encoding="utf-8")
        (staged / "trainee.ditaval").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<val/>\n',
            encoding="utf-8",
        )
        return staged

    def test_publish_invokes_dita_ot_per_edition_per_ditamap(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            staged = self._make_staged(tmp)
            out_root = tmp / "html"

            with mock.patch.object(publish_html, "subprocess") as mock_sub:
                mock_sub.run.return_value = mock.Mock(
                    returncode=0, stdout="", stderr="",
                )
                rc = publish(Path("/opt/dita-ot"), staged, out_root)

            self.assertEqual(rc, 0)
            # 2 editions × 2 ditamaps = 4 invocations
            self.assertEqual(mock_sub.run.call_count, 4)
            calls = [c.args[0] for c in mock_sub.run.call_args_list]

            # Two student calls carry --filter=…/trainee.ditaval
            student_calls = [
                argv for argv in calls
                if any(arg.startswith("--filter=") for arg in argv)
            ]
            self.assertEqual(len(student_calls), 2)
            for argv in student_calls:
                self.assertTrue(any(
                    arg.endswith("trainee.ditaval")
                    for arg in argv if arg.startswith("--filter=")
                ), f"student call missing trainee filter: {argv}")
                self.assertTrue(any(
                    "/student/" in arg for arg in argv
                    if arg.startswith("--output=")
                ), f"student call output not in /student/: {argv}")

            # Two instructor calls carry no --filter
            instructor_calls = [
                argv for argv in calls
                if not any(arg.startswith("--filter=") for arg in argv)
            ]
            self.assertEqual(len(instructor_calls), 2)
            for argv in instructor_calls:
                self.assertTrue(any(
                    "/instructor/" in arg for arg in argv
                    if arg.startswith("--output=")
                ), f"instructor call output not in /instructor/: {argv}")

    def test_publish_fails_loudly_when_ditaval_missing(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            staged = self._make_staged(tmp)
            (staged / "trainee.ditaval").unlink()  # remove the profile

            with mock.patch.object(publish_html, "subprocess") as mock_sub:
                mock_sub.run.return_value = mock.Mock(
                    returncode=0, stdout="", stderr="",
                )
                rc = publish(Path("/opt/dita-ot"), staged, tmp / "html")

            self.assertNotEqual(rc, 0,
                                "publisher must exit non-zero when DITAVAL is missing")

    def test_publish_logs_filter_per_edition(self):
        """FR-011: log clearly which audience filter (if any) was applied."""
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            staged = self._make_staged(tmp)

            with mock.patch.object(publish_html, "subprocess") as mock_sub, \
                 mock.patch("builtins.print") as mock_print:
                mock_sub.run.return_value = mock.Mock(
                    returncode=0, stdout="", stderr="",
                )
                publish(Path("/opt/dita-ot"), staged, tmp / "html")

            log_lines = [
                str(c.args[0]) for c in mock_print.call_args_list if c.args
            ]
            instructor_logs = [l for l in log_lines if "[publish:instructor]" in l]
            student_logs = [l for l in log_lines if "[publish:student]" in l]
            self.assertEqual(len(instructor_logs), 2,
                             "one log line per instructor ditamap")
            self.assertEqual(len(student_logs), 2,
                             "one log line per student ditamap")
            for line in instructor_logs:
                self.assertIn("filter=none", line)
            for line in student_logs:
                self.assertIn("filter=", line)
                self.assertIn("trainee.ditaval", line)


# -----------------------------------------------------------------------------
# Spec 003 — Edition index pages and shared landing page
# -----------------------------------------------------------------------------

class EditionIndexTests(unittest.TestCase):

    def test_writes_index_at_subdir_root(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            subdir = tmp / "instructor"
            edition = next(e for e in EDITIONS if e.name == "instructor")
            entries = [("Main", "main"), ("Progress Test 1", "progress-test-1")]
            path = write_edition_index(subdir, edition, entries, "2026-01-01 00:00 UTC")
            self.assertTrue(path.is_file())
            html = path.read_text(encoding="utf-8")
            self.assertIn("Instructor edition", html)
            self.assertIn('href="main/index.html"', html)
            self.assertIn('href="progress-test-1/index.html"', html)
            self.assertIn("Generated 2026-01-01 00:00 UTC", html)

    def test_student_index_does_not_carry_instructor_word_in_heading(self):
        """The student-edition index page must not contain 'Instructor'."""
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            subdir = tmp / "student"
            edition = next(e for e in EDITIONS if e.name == "student")
            entries = [("Main", "main")]
            path = write_edition_index(subdir, edition, entries, "2026-01-01 00:00 UTC")
            html = path.read_text(encoding="utf-8")
            self.assertNotIn("Instructor", html,
                             "student-edition index page must not contain 'Instructor'")


class SharedLandingTests(unittest.TestCase):

    def test_shared_landing_links_to_both_editions_in_order(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            path = write_shared_landing(tmp, EDITIONS, "2026-01-01 00:00 UTC")
            html = path.read_text(encoding="utf-8")
            self.assertIn('href="instructor/index.html"', html)
            self.assertIn('href="student/index.html"', html)
            self.assertLess(
                html.index('href="instructor/index.html"'),
                html.index('href="student/index.html"'),
                "instructor link must appear before student link (deterministic order)",
            )
            self.assertIn("Generated 2026-01-01 00:00 UTC", html)

    def test_shared_landing_is_byte_deterministic_given_fixed_timestamp(self):
        with TemporaryDirectory() as tmp_str:
            tmp1 = Path(tmp_str) / "a"
            tmp2 = Path(tmp_str) / "b"
            ts = "2026-01-01 00:00 UTC"
            p1 = write_shared_landing(tmp1, EDITIONS, ts)
            p2 = write_shared_landing(tmp2, EDITIONS, ts)
            self.assertEqual(
                p1.read_bytes(), p2.read_bytes(),
                "two writes with the same timestamp must be byte-identical",
            )


# -----------------------------------------------------------------------------
# Spec 003 — Idempotency scrub
# -----------------------------------------------------------------------------

class ScrubMetadataTests(unittest.TestCase):

    def test_strips_dc_date_created_meta(self):
        with TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            (root / "a.html").write_text(
                '<html><head><meta charset="UTF-8">'
                '<meta name="DC.date.created" content="2026-05-16T12:34:56Z"/>'
                '<title>T</title></head><body><p>x</p></body></html>',
                encoding="utf-8",
            )
            scrub_nondeterministic_metadata(root)
            content = (root / "a.html").read_text(encoding="utf-8")
            self.assertNotIn("DC.date.created", content)
            self.assertNotIn("2026-05-16T12:34:56Z", content)
            # Other metadata is preserved.
            self.assertIn('<meta charset="UTF-8">', content)
            self.assertIn("<title>T</title>", content)

    def test_strips_dc_date_modified_meta(self):
        with TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            (root / "a.html").write_text(
                '<html><head>'
                '<meta name="DC.date.modified" content="2026-05-16T12:34:56Z"/>'
                '</head></html>',
                encoding="utf-8",
            )
            scrub_nondeterministic_metadata(root)
            self.assertNotIn(
                "DC.date.modified",
                (root / "a.html").read_text(encoding="utf-8"),
            )

    def test_idempotent_when_no_metadata_present(self):
        with TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            html = '<html><head><title>T</title></head><body><p>x</p></body></html>'
            (root / "a.html").write_text(html, encoding="utf-8")
            scrub_nondeterministic_metadata(root)
            self.assertEqual(
                (root / "a.html").read_text(encoding="utf-8"),
                html,
                "files without metadata must be untouched",
            )


# -----------------------------------------------------------------------------
# GramFrame plugin injection
# -----------------------------------------------------------------------------


class InjectGramframePluginTests(unittest.TestCase):
    """The publisher vendors gramframe.bundle.js next to ``html/`` and links
    it from every emitted page, so the gram-config tables DITA-OT
    produces become interactive viewers in the browser."""

    @staticmethod
    def _write(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")

    @staticmethod
    def _fake_bundle(tmp: Path) -> Path:
        src = tmp / "vendor" / "gramframe.bundle.js"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("/* gramframe stub */\n", encoding="utf-8", newline="\n")
        return src

    def _gram_page(self) -> str:
        return (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n'
            '  <head>\n'
            '    <meta charset="UTF-8">\n'
            '    <title>Gram</title>\n'
            '  </head>\n'
            '  <body>\n'
            '    <table class="gram-config"><tr><td colspan="2">'
            '<img src="g.png"></td></tr></table>\n'
            '  </body>\n'
            '</html>\n'
        )

    def test_copies_bundle_to_out_root(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            out.mkdir()
            src = self._fake_bundle(tmp)
            self._write(out / "index.html", self._gram_page())
            inject_gramframe_plugin(out, bundle_src=src)
            self.assertTrue((out / GRAMFRAME_BUNDLE_NAME).is_file())
            self.assertEqual(
                (out / GRAMFRAME_BUNDLE_NAME).read_text(encoding="utf-8"),
                "/* gramframe stub */\n",
            )

    def test_injects_script_into_head_of_every_html_file(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            src = self._fake_bundle(tmp)
            self._write(out / "index.html", self._gram_page())
            self._write(
                out / "instructor" / "main" / "main" / "gram-01" / "gram_01.html",
                self._gram_page(),
            )
            count = inject_gramframe_plugin(out, bundle_src=src)
            self.assertEqual(count, 2)

            top = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn(
                '<script src="gramframe.bundle.js" defer></script>',
                top,
            )

            deep = (
                out / "instructor" / "main" / "main" / "gram-01" / "gram_01.html"
            ).read_text(encoding="utf-8")
            # Deep page must reach four levels up to the bundle at out_root.
            self.assertIn(
                '<script src="../../../../gramframe.bundle.js" defer></script>',
                deep,
            )

    def test_script_tag_sits_inside_head(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            out.mkdir()
            src = self._fake_bundle(tmp)
            self._write(out / "index.html", self._gram_page())
            inject_gramframe_plugin(out, bundle_src=src)
            body = (out / "index.html").read_text(encoding="utf-8")
            head_open = body.index("<head>")
            head_close = body.index("</head>")
            script_at = body.index("gramframe.bundle.js")
            self.assertLess(head_open, script_at)
            self.assertLess(script_at, head_close)

    def test_is_idempotent(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            out.mkdir()
            src = self._fake_bundle(tmp)
            self._write(out / "index.html", self._gram_page())
            first = inject_gramframe_plugin(out, bundle_src=src)
            after_once = (out / "index.html").read_text(encoding="utf-8")
            second = inject_gramframe_plugin(out, bundle_src=src)
            after_twice = (out / "index.html").read_text(encoding="utf-8")
            self.assertEqual(first, 1)
            self.assertEqual(second, 0)
            self.assertEqual(after_once, after_twice)
            self.assertEqual(
                after_twice.count('src="gramframe.bundle.js"'), 1,
            )

    def test_raises_when_bundle_missing(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            out.mkdir()
            with self.assertRaises(FileNotFoundError):
                inject_gramframe_plugin(
                    out, bundle_src=tmp / "does-not-exist.js",
                )

    def test_vendored_bundle_is_present_in_repo(self):
        """The v0.1.9 bundle must be committed alongside the publisher."""
        self.assertTrue(
            publish_html.GRAMFRAME_BUNDLE_SRC.is_file(),
            f"Vendor the GramFrame bundle at "
            f"{publish_html.GRAMFRAME_BUNDLE_SRC.relative_to(REPO_ROOT)}",
        )


# -----------------------------------------------------------------------------
# Operator Console v2 dark-theme injection
# -----------------------------------------------------------------------------


class InjectOperatorConsoleThemeTests(unittest.TestCase):
    """Wire theme.css into every emitted HTML page, with the right body
    classification and data-edition for the page type."""

    @staticmethod
    def _fake_theme(tmp: Path) -> Path:
        src = tmp / "vendor" / "theme.css"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("/* operator console */\n", encoding="utf-8", newline="\n")
        return src

    @staticmethod
    def _write(path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8", newline="\n")

    @staticmethod
    def _shell(body_tag: str = "<body>") -> str:
        return (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n'
            '  <head>\n'
            '    <meta charset="UTF-8">\n'
            '    <title>X</title>\n'
            '  </head>\n'
            f'  {body_tag}\n'
            '    <p>x</p>\n'
            '  </body>\n'
            '</html>\n'
        )

    def test_drops_theme_at_root_and_each_edition(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            self._write(out / "index.html", self._shell())
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            self.assertTrue((out / THEME_BUNDLE_NAME).is_file())
            self.assertTrue((out / "instructor" / THEME_BUNDLE_NAME).is_file())
            self.assertTrue((out / "student" / THEME_BUNDLE_NAME).is_file())

    def test_shared_landing_gets_landing_class_and_no_edition(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            self._write(out / "index.html", self._shell())
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            body = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('<link rel="stylesheet" type="text/css" href="theme.css">', body)
            self.assertIn('class="landing"', body)
            self.assertNotIn("data-edition", body)

    def test_edition_index_gets_edition_index_class(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            self._write(out / "instructor" / "index.html", self._shell())
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            body = (out / "instructor" / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-edition="instructor"', body)
            self.assertIn('class="edition-index"', body)
            self.assertIn('href="theme.css"', body)

    def test_publication_index_gets_ditamap_index_class(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            self._write(out / "instructor" / "main" / "index.html", self._shell())
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            body = (out / "instructor" / "main" / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-edition="instructor"', body)
            self.assertIn('class="ditamap-index"', body)
            self.assertIn('href="../theme.css"', body)

    def test_topic_page_gets_edition_only_and_relative_theme_href(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            topic = (
                out / "instructor" / "main" / "main" / "week-2-grams"
                / "gram-20" / "gram_20.html"
            )
            self._write(topic, self._shell('<body id="gram_20">'))
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            body = topic.read_text(encoding="utf-8")
            self.assertIn('data-edition="instructor"', body)
            self.assertNotIn('class="ditamap-index"', body)
            self.assertNotIn('class="landing"', body)
            self.assertNotIn('class="edition-index"', body)
            # Theme css is at out/instructor/theme.css; gram_20.html lives
            # four directories below that under instructor/main/main/
            # week-2-grams/gram-20/.
            self.assertIn(
                '<link rel="stylesheet" type="text/css" href="../../../../theme.css">',
                body,
            )
            # Existing body attributes are preserved.
            self.assertIn('id="gram_20"', body)

    def test_student_edition_is_tagged(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            topic = out / "student" / "main" / "main" / "gram-01" / "gram_01.html"
            self._write(topic, self._shell())
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            body = topic.read_text(encoding="utf-8")
            self.assertIn('data-edition="student"', body)

    def test_is_idempotent(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            self._write(out / "instructor" / "main" / "index.html", self._shell())
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            once = (out / "instructor" / "main" / "index.html").read_text(encoding="utf-8")
            inject_operator_console_theme(out, bundle_src=self._fake_theme(tmp))
            twice = (out / "instructor" / "main" / "index.html").read_text(encoding="utf-8")
            self.assertEqual(once, twice)
            self.assertEqual(once.count('href="../theme.css"'), 1)
            self.assertEqual(once.count('data-edition='), 1)
            self.assertEqual(once.count('class="ditamap-index"'), 1)

    def test_raises_when_bundle_missing(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            out = tmp / "html"
            out.mkdir()
            with self.assertRaises(FileNotFoundError):
                inject_operator_console_theme(
                    out, bundle_src=tmp / "does-not-exist.css",
                )

    def test_vendored_theme_is_present_in_repo(self):
        self.assertTrue(
            publish_html.THEME_BUNDLE_SRC.is_file(),
            f"Vendor the Operator Console v2 theme at "
            f"{publish_html.THEME_BUNDLE_SRC.relative_to(REPO_ROOT)}",
        )


# -----------------------------------------------------------------------------
# Spec 003 — Deterministic timestamp helper
# -----------------------------------------------------------------------------

class GeneratedTimestampTests(unittest.TestCase):

    def test_honours_source_date_epoch_when_set(self):
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1700000000"}):
            self.assertEqual(
                publish_html._generated_timestamp(),
                "2023-11-14 22:13 UTC",
            )

    def test_falls_back_to_fixed_string_when_unset(self):
        env = {k: v for k, v in os.environ.items() if k != "SOURCE_DATE_EPOCH"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(publish_html._generated_timestamp(), "unset")

    def test_falls_back_when_value_is_garbage(self):
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "not-a-number"}):
            self.assertEqual(publish_html._generated_timestamp(), "unset")


# -----------------------------------------------------------------------------
# Spec 003 — End-to-end publisher idempotency (FR-008 / SC-006)
# -----------------------------------------------------------------------------

class PublisherIdempotencyTests(unittest.TestCase):
    """Two consecutive `main()` runs over the same source tree, with a
    fixed SOURCE_DATE_EPOCH and deterministic mocked DITA-OT output,
    produce byte-identical html/ trees."""

    def _fake_dita_ot(self, *args, **kwargs):
        """subprocess.run replacement: emit a deterministic gram_01.html
        plus a wall-clock <meta name="DC.date.created"> the scrub strips."""
        argv = args[0]
        output_arg = next(a for a in argv if a.startswith("--output="))
        output_dir = Path(output_arg.removeprefix("--output="))
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "gram_01.html").write_text(
            '<html><head><meta charset="UTF-8">'
            '<meta name="DC.date.created" content="'
            + datetime.now(timezone.utc).isoformat() +
            '"/>'
            '<title>Gram 01</title></head>'
            '<body><h1>Gram 01</h1></body></html>',
            encoding="utf-8",
        )
        (output_dir / "index.html").write_text(
            '<html><body><a href="gram_01.html">Gram 01</a></body></html>',
            encoding="utf-8",
        )
        return mock.Mock(returncode=0, stdout="", stderr="")

    def _hash_tree(self, root: Path) -> dict[str, str]:
        import hashlib
        hashes = {}
        for path in sorted(root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                hashes[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        return hashes

    def test_two_main_runs_are_byte_identical(self):
        with TemporaryDirectory() as tmp_str:
            tmp = Path(tmp_str)
            # Two minimal DITA source trees with the trainee.ditaval profile.
            for variant in ("a", "b"):
                d = tmp / variant / "dita"
                d.mkdir(parents=True)
                (d / "main.ditamap").write_text(
                    '<map><title>Main</title></map>', encoding="utf-8",
                )
                (d / "trainee.ditaval").write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n<val/>\n',
                    encoding="utf-8",
                )

            fake_dita_ot = tmp / "dita-ot"
            (fake_dita_ot / "bin").mkdir(parents=True)
            (fake_dita_ot / "bin" / "dita").write_text("#!/bin/sh\n")

            def run_once(variant: str) -> Path:
                out = tmp / variant / "html"
                staged = tmp / variant / ".dita-build"
                with mock.patch.object(publish_html, "subprocess") as mock_sub, \
                     mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1700000000"}):
                    mock_sub.run.side_effect = self._fake_dita_ot
                    rc = publish_html.main([
                        "--dita", str(tmp / variant / "dita"),
                        "--out", str(out),
                        "--dita-ot", str(fake_dita_ot),
                        "--staged", str(staged),
                    ])
                self.assertEqual(rc, 0)
                return out

            out_a = run_once("a")
            out_b = run_once("b")
            self.assertEqual(self._hash_tree(out_a), self._hash_tree(out_b),
                             "html/ trees from two main() runs must be byte-identical")


def _html_twin(dita_path: Path) -> Path:
    """Return the HTML file produced by DITA-OT for ``dita_path``.

    DITA-OT writes each ditamap's output under
    ``html/<edition>/<map>/<map>/...`` — the map stem appears twice
    because DITA-OT preserves the source tree relative to the build
    root, and we hand it the staged ditamap copy. The image-presence
    regression check targets the **instructor edition** (the
    unfiltered superset) — that's where every image referenced by
    ``dita/`` is required to exist. Student-edition image presence is
    implicitly verified by the Jest URL-parity test, which asserts
    each instructor HTML page has a sibling at the same path under
    ``html/student/``.
    """
    rel = dita_path.relative_to(DITA_ROOT)
    map_stem = rel.parts[0]
    inner = Path(*rel.parts[1:]).with_suffix(".html")
    return HTML_ROOT / "instructor" / map_stem / map_stem / inner


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

"""Tests for the HTML pretty-printer used by ``publish_html.py``.

The publish pipeline shells out to DITA-OT (a Java tool) which we cannot
run inside ``unittest``. ``prettify_html`` is purely string-in /
string-out, so we exercise it directly against DITA-OT-shaped fixtures.
"""

from __future__ import annotations

import os
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import publish_html
from publish_html import (
    EDITIONS,
    Edition,
    _dita_ot_command,
    prettify_html,
    prettify_tree,
    publish,
    scrub_nondeterministic_metadata,
    write_edition_index,
    write_shared_landing,
)


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


if __name__ == "__main__":
    unittest.main()

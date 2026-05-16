"""Publish the generated DITA tree to HTML using DITA-OT.

The DITA source files in ``dita/`` deliberately omit DOCTYPE declarations
(contract: Oxygen handles DTD validation at publish time). DITA-OT,
however, needs DOCTYPEs to classify the elements. This script stages a
build copy of ``dita/`` with DOCTYPEs injected, runs DITA-OT once per
ditamap, and writes the results under ``html/``.

After DITA-OT runs, every generated ``*.html`` file is reformatted in
place so reviewers can read it. DITA-OT emits topic pages on a single
long line, which is unreadable in a diff or browser view-source.

The source ``dita/`` tree is never modified.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

TOPIC_DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE topic PUBLIC "-//OASIS//DTD DITA Topic//EN" "topic.dtd">\n'
)
MAP_DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE map PUBLIC "-//OASIS//DTD DITA Map//EN" "map.dtd">\n'
)

LOGGER = logging.getLogger("publish_html")


# -----------------------------------------------------------------------------
# Editions — spec 003
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Edition:
    """A single named HTML rendering of every publication for one audience.

    Exactly two editions exist (per spec 003 FR-013 / Out of Scope):

    - ``instructor`` — no audience filter; the full content, including
      vessel-name decorations, Analysis Sheets, and "Instructor Version"
      labelling.
    - ``student`` — DITA-OT runs with ``--filter=<dita>/trainee.ditaval``
      to strip every element carrying ``audience="-trainee"``.

    See ``specs/003-instructor-student-versions/contracts/audience-filter.md``
    for the DITAVAL profile shape and ``contracts/html-edition-layout.md``
    for the output tree layout.
    """

    name: str
    output_subdir: str
    ditaval: Path | None
    description: str


EDITIONS: tuple[Edition, ...] = (
    Edition(
        name="instructor",
        output_subdir="instructor",
        ditaval=None,
        description=(
            "Full content, including answers, vessel names, and analysis sheets."
        ),
    ),
    Edition(
        name="student",
        output_subdir="student",
        ditaval=Path("trainee.ditaval"),
        description=(
            "Exercises only, with answers, vessel names, and analysis sheets "
            "removed."
        ),
    ),
)


def stage(src: Path, dst: Path) -> None:
    """Copy src to dst and add DOCTYPEs to topics and ditamaps."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for path in dst.rglob("*.dita"):
        body = path.read_text(encoding="utf-8")
        path.write_text(TOPIC_DOCTYPE + body, encoding="utf-8", newline="\n")
    for path in sorted(dst.glob("*.ditamap")):
        body = path.read_text(encoding="utf-8")
        path.write_text(MAP_DOCTYPE + body, encoding="utf-8", newline="\n")


VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
})

INLINE_ELEMENTS = frozenset({
    "a", "abbr", "b", "bdi", "bdo", "br", "cite", "code", "data", "dfn",
    "em", "i", "img", "input", "kbd", "label", "mark", "q", "s", "samp",
    "small", "span", "strong", "sub", "sup", "time", "u", "var", "wbr",
})

# Content inside these elements is preserved byte-for-byte: HTML semantic
# whitespace (<pre>, <textarea>) and CDATA-mode content (<script>, <style>).
PRESERVE_WHITESPACE = frozenset({"pre", "textarea", "script", "style"})


class _Element:
    __slots__ = ("tag", "attrs", "children", "void")

    def __init__(self, tag: str, attrs: list, void: bool = False) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list = []
        self.void = void


class _Text:
    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        self.data = data


class _Raw:
    """DOCTYPE, comment, or processing instruction — emitted verbatim."""

    __slots__ = ("data",)

    def __init__(self, data: str) -> None:
        self.data = data


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = _Element("", [])
        self.stack: list = [self.root]

    def handle_starttag(self, tag, attrs):
        is_void = tag in VOID_ELEMENTS
        node = _Element(tag, attrs, void=is_void)
        self.stack[-1].children.append(node)
        if not is_void:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Element(tag, attrs, void=True))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(_Text(data))

    def handle_entityref(self, name):
        self.stack[-1].children.append(_Text(f"&{name};"))

    def handle_charref(self, name):
        self.stack[-1].children.append(_Text(f"&#{name};"))

    def handle_comment(self, data):
        self.stack[-1].children.append(_Raw(f"<!--{data}-->"))

    def handle_decl(self, decl):
        self.stack[-1].children.append(_Raw(f"<!{' '.join(decl.split())}>"))

    def handle_pi(self, data):
        self.stack[-1].children.append(_Raw(f"<?{data}>"))


def _format_attrs(attrs: list) -> str:
    if not attrs:
        return ""
    parts = []
    for name, value in attrs:
        if value is None:
            parts.append(name)
        else:
            escaped = (value.replace("&", "&amp;")
                            .replace('"', "&quot;")
                            .replace("<", "&lt;"))
            parts.append(f'{name}="{escaped}"')
    return " " + " ".join(parts)


def _is_inline_subtree(node) -> bool:
    if isinstance(node, _Text):
        return True
    if isinstance(node, _Raw):
        return False
    if node.tag and node.tag not in INLINE_ELEMENTS:
        return False
    return all(_is_inline_subtree(c) for c in node.children)


def _emit(buf: list, node, depth: int, indent: str) -> None:
    if isinstance(node, (_Text, _Raw)):
        buf.append(node.data)
        return
    attrs = _format_attrs(node.attrs)
    if node.void:
        buf.append(f"<{node.tag}{attrs}>")
        return
    if not node.children:
        buf.append(f"<{node.tag}{attrs}></{node.tag}>")
        return
    if node.tag in PRESERVE_WHITESPACE:
        buf.append(f"<{node.tag}{attrs}>")
        for c in node.children:
            _emit(buf, c, depth, indent)
        buf.append(f"</{node.tag}>")
        return
    if all(_is_inline_subtree(c) for c in node.children):
        buf.append(f"<{node.tag}{attrs}>")
        for c in node.children:
            _emit(buf, c, depth, indent)
        buf.append(f"</{node.tag}>")
        return
    buf.append(f"<{node.tag}{attrs}>")
    child_pad = "\n" + indent * (depth + 1)
    for c in node.children:
        if isinstance(c, _Text):
            stripped = c.data.strip()
            if stripped:
                buf.append(child_pad)
                buf.append(stripped)
            continue
        buf.append(child_pad)
        _emit(buf, c, depth + 1, indent)
    buf.append("\n" + indent * depth + f"</{node.tag}>")


def prettify_html(source: str, indent: str = "  ") -> str:
    """Re-emit ``source`` with block elements on their own indented line.

    Elements whose entire subtree is inline (``<a>``, ``<span>``,
    ``<strong>``, plain text…) stay flat — splitting them would change
    rendered whitespace. ``<pre>`` / ``<script>`` / ``<style>`` content
    is preserved verbatim. Void elements (``<meta>``, ``<br>``, ``<img>``,
    ``<link>``) are emitted HTML5-style with no trailing slash.
    """
    builder = _TreeBuilder()
    builder.feed(source)
    builder.close()
    buf: list = []
    first = True
    for c in builder.root.children:
        if isinstance(c, _Text):
            stripped = c.data.strip()
            if not stripped:
                continue
            if not first:
                buf.append("\n")
            buf.append(stripped)
        else:
            if not first:
                buf.append("\n")
            _emit(buf, c, 0, indent)
        first = False
    buf.append("\n")
    return "".join(buf)


def prettify_tree(root: Path) -> int:
    count = 0
    for path in root.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        path.write_text(prettify_html(original), encoding="utf-8", newline="\n")
        count += 1
    return count


# DITA-OT bakes wall-clock-derived metadata into every emitted HTML page,
# which would defeat the byte-deterministic publish requirement
# (FR-008 / SC-006). The two known carriers are:
#
# 1. A ``<meta name="DC.date.created" content="…"/>`` element in <head>.
# 2. A trailing ``<meta name="DC.date.modified" content="…"/>`` element.
#
# Both reflect the DITA-OT run wall-clock, not anything about the
# source. Stripping them outright keeps the rendered HTML byte-stable
# across runs without losing any information a reader cares about.
_DITAOT_DATE_META_RE = re.compile(
    r'\s*<meta[^>]+name="DC\.date\.(?:created|modified)"[^>]*>\s*',
    re.IGNORECASE,
)


def scrub_nondeterministic_metadata(root: Path) -> int:
    """Strip DITA-OT wall-clock metadata from every HTML file under ``root``.

    See ``research.md`` R7 and ``contracts/audience-filter.md`` §4.
    Returns the number of files inspected (every ``*.html`` walked is
    counted, whether or not metadata was actually present).
    """
    count = 0
    for path in root.rglob("*.html"):
        original = path.read_text(encoding="utf-8")
        scrubbed = _DITAOT_DATE_META_RE.sub("", original)
        if scrubbed != original:
            path.write_text(scrubbed, encoding="utf-8", newline="\n")
        count += 1
    return count


_TITLE_RE = re.compile(r'<map[^>]*\btitle="([^"]*)"', re.IGNORECASE)


def _ditamap_title(ditamap: Path) -> str:
    match = _TITLE_RE.search(ditamap.read_text(encoding="utf-8"))
    return match.group(1) if match else ditamap.stem


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _generated_timestamp() -> str:
    """Return a generation timestamp suitable for the landing-page chrome.

    Honours ``SOURCE_DATE_EPOCH`` for byte-deterministic output across
    runs (research R6 / FR-008 / SC-006). Falls back to the literal
    string ``"unset"`` when the environment variable is not present, so
    a missing variable produces a stable known string rather than the
    wall-clock time.
    """
    import os
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            ts = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
            return ts.strftime("%Y-%m-%d %H:%M UTC")
        except (TypeError, ValueError):
            pass
    return "unset"


def write_edition_index(
    out_subdir: Path,
    edition: Edition,
    entries: list[tuple[str, str]],
    generated_at: str,
) -> Path:
    """Write a per-edition publication index at ``out_subdir/index.html``.

    Replaces the legacy ``write_root_index()`` shape: one index per
    edition, scoped to that edition's output subtree. Link hrefs are
    ``<stem>/index.html`` (relative to ``out_subdir``).
    """
    items = "\n".join(
        f'      <li><a href="{_escape(href)}/index.html">{_escape(title)}</a></li>'
        for title, href in entries
    )
    edition_name = edition.name.title()
    out_subdir.mkdir(parents=True, exist_ok=True)
    index_path = out_subdir / "index.html"
    index_path.write_text(
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '  <head>\n'
        '    <meta charset="UTF-8">\n'
        f'    <title>{edition_name} edition — published DITA output</title>\n'
        '  </head>\n'
        '  <body>\n'
        f'    <h1>{edition_name} edition</h1>\n'
        f'    <p>Generated {generated_at}</p>\n'
        '    <ul>\n'
        f'{items}\n'
        '    </ul>\n'
        '  </body>\n'
        '</html>\n',
        encoding="utf-8",
        newline="\n",
    )
    return index_path


def write_shared_landing(
    out_root: Path,
    editions: tuple[Edition, ...],
    generated_at: str,
) -> Path:
    """Write the shared top-level ``html/index.html`` (spec 003 FR-006).

    One link per edition, in the order ``editions`` defines, each with
    a one-sentence audience description sourced from
    ``Edition.description``. This is the authoritative entry point
    after spec 003 — pre-existing ``html/<publication>/`` deep links
    no longer resolve (research R8).
    """
    items = "\n".join(
        f'      <li><a href="{_escape(ed.output_subdir)}/index.html">'
        f'<strong>{_escape(ed.name.title())} edition</strong></a> — '
        f'{_escape(ed.description)}</li>'
        for ed in editions
    )
    out_root.mkdir(parents=True, exist_ok=True)
    index_path = out_root / "index.html"
    index_path.write_text(
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '  <head>\n'
        '    <meta charset="UTF-8">\n'
        '    <title>Published DITA output — choose an edition</title>\n'
        '  </head>\n'
        '  <body>\n'
        '    <h1>Published DITA output</h1>\n'
        f'    <p>Generated {generated_at}</p>\n'
        '    <ul>\n'
        f'{items}\n'
        '    </ul>\n'
        '  </body>\n'
        '</html>\n',
        encoding="utf-8",
        newline="\n",
    )
    return index_path


def _dita_ot_command(
    dita_ot: Path,
    ditamap: Path,
    target: Path,
    ditaval: Path | None,
) -> list[str]:
    """Build the argv for one DITA-OT invocation.

    Extracted so ``tests/test_publish_html.py`` can assert on the
    command shape without invoking the Java toolchain.
    """
    argv = [
        str(dita_ot / "bin" / "dita"),
        f"--input={ditamap}",
        "--format=html5",
        f"--output={target}",
        "--processing-mode=lax",
    ]
    if ditaval is not None:
        argv.append(f"--filter={ditaval}")
    return argv


def publish(
    dita_ot: Path,
    staged: Path,
    out_root: Path,
    editions: tuple[Edition, ...] = EDITIONS,
) -> int:
    """Run DITA-OT once per ditamap per edition.

    For each ditamap, the publisher emits two HTML trees:
    ``<out_root>/instructor/<stem>/`` (no audience filter) and
    ``<out_root>/student/<stem>/`` (with ``--filter=<dita>/trainee.ditaval``).
    Both editions are produced from the *same* staged DITA source tree —
    no per-edition forking, no post-publish rewriting (FR-013).

    The DITAVAL profile is resolved against ``staged`` (the staging
    directory, not the original ``dita/``) so the path passed to
    DITA-OT remains stable across runs and the staged tree is fully
    self-contained.
    """
    ditamaps = sorted(staged.glob("*.ditamap"))
    if not ditamaps:
        print(f"No ditamaps found under {staged}", file=sys.stderr)
        return 1
    errors = 0
    for edition in editions:
        filter_path: Path | None = None
        if edition.ditaval is not None:
            filter_path = (staged / edition.ditaval).resolve()
            if not filter_path.is_file():
                print(
                    f"DITAVAL profile missing for edition {edition.name!r}: "
                    f"{filter_path}",
                    file=sys.stderr,
                )
                return 1
        for ditamap in ditamaps:
            target = out_root / edition.output_subdir / ditamap.stem
            filter_label = str(filter_path) if filter_path is not None else "none"
            LOGGER.info(
                "[publish:%s] %s -> %s (filter=%s)",
                edition.name, ditamap.name, target, filter_label,
            )
            print(
                f"[publish:{edition.name}] {ditamap.name} -> {target} "
                f"(filter={filter_label})"
            )
            target.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                _dita_ot_command(dita_ot, ditamap, target, filter_path),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors += 1
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
    return 0 if errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dita", default=Path("dita"), type=Path)
    parser.add_argument("--out", default=Path("html"), type=Path)
    parser.add_argument("--dita-ot", required=True, type=Path)
    parser.add_argument("--staged", default=Path(".dita-build"), type=Path)
    args = parser.parse_args(argv)

    if not args.dita.is_dir():
        print(f"Source dita tree not found: {args.dita}", file=sys.stderr)
        return 1
    if not (args.dita / "trainee.ditaval").is_file():
        print(
            f"Required DITAVAL profile missing: {args.dita / 'trainee.ditaval'}.\n"
            "Spec 003 makes the dual-edition publish the only supported mode; "
            "the trainee filter must be committed alongside the DITA source.",
            file=sys.stderr,
        )
        return 1
    if not (args.dita_ot / "bin" / "dita").exists():
        print(f"DITA-OT not found at {args.dita_ot}", file=sys.stderr)
        return 1

    print(f"[stage] {args.dita} -> {args.staged}")
    stage(args.dita, args.staged)

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    rc = publish(args.dita_ot, args.staged, args.out)

    if rc == 0:
        entries = [
            (_ditamap_title(m), m.stem)
            for m in sorted(args.staged.glob("*.ditamap"))
        ]
        generated_at = _generated_timestamp()
        for edition in EDITIONS:
            edition_index = write_edition_index(
                args.out / edition.output_subdir, edition, entries, generated_at,
            )
            print(
                f"[index] wrote {edition_index} ({len(entries)} entries)"
            )
        landing = write_shared_landing(args.out, EDITIONS, generated_at)
        print(f"[index] wrote {landing} (shared landing)")
        formatted = prettify_tree(args.out)
        print(f"[prettify] reformatted {formatted} HTML file(s) under {args.out}")
        scrubbed = scrub_nondeterministic_metadata(args.out)
        print(f"[scrub] stripped DITA-OT timestamps from {scrubbed} file(s)")

    shutil.rmtree(args.staged, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())

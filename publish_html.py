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
import re
import shutil
import subprocess
import sys
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


_TITLE_RE = re.compile(r'<map[^>]*\btitle="([^"]*)"', re.IGNORECASE)


def _ditamap_title(ditamap: Path) -> str:
    match = _TITLE_RE.search(ditamap.read_text(encoding="utf-8"))
    return match.group(1) if match else ditamap.stem


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def write_root_index(out_root: Path, entries: list[tuple[str, str]]) -> None:
    """Write html/index.html with one link per ditamap landing page."""
    items = "\n".join(
        f'      <li><a href="{_escape(href)}/index.html">{_escape(title)}</a></li>'
        for title, href in entries
    )
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out_root.joinpath("index.html").write_text(
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '  <head>\n'
        '    <meta charset="UTF-8">\n'
        '    <title>Published DITA output</title>\n'
        '  </head>\n'
        '  <body>\n'
        '    <h1>Published DITA output</h1>\n'
        f'    <p>Generated {generated}</p>\n'
        '    <ul>\n'
        f'{items}\n'
        '    </ul>\n'
        '  </body>\n'
        '</html>\n',
        encoding="utf-8",
        newline="\n",
    )


def publish(dita_ot: Path, staged: Path, out_root: Path) -> int:
    ditamaps = sorted(staged.glob("*.ditamap"))
    if not ditamaps:
        print(f"No ditamaps found under {staged}", file=sys.stderr)
        return 1
    errors = 0
    for ditamap in ditamaps:
        target = out_root / ditamap.stem
        print(f"[publish] {ditamap.name} -> {target}")
        target.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [
                str(dita_ot / "bin" / "dita"),
                f"--input={ditamap}",
                "--format=html5",
                f"--output={target}",
                "--processing-mode=lax",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            errors += 1
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
    return 0 if errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dita", default=Path("dita"), type=Path)
    parser.add_argument("--out", default=Path("html"), type=Path)
    parser.add_argument("--dita-ot", required=True, type=Path)
    parser.add_argument("--staged", default=Path(".dita-build"), type=Path)
    args = parser.parse_args(argv)

    if not args.dita.is_dir():
        print(f"Source dita tree not found: {args.dita}", file=sys.stderr)
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
        write_root_index(args.out, entries)
        print(f"[index] wrote {args.out / 'index.html'} ({len(entries)} entries)")
        formatted = prettify_tree(args.out)
        print(f"[prettify] reformatted {formatted} HTML file(s) under {args.out}")

    shutil.rmtree(args.staged, ignore_errors=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())

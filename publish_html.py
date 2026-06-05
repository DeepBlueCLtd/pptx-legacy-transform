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
import os
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


def _write_text(path: Path, text: str) -> None:
    """Write ``text`` with LF endings, working on Python 3.9.

    ``Path.write_text`` only grew a ``newline`` parameter in 3.10; the
    air-gapped target runs WinPython 3.9, so force LF via ``open`` to
    preserve the byte-identical-output contract.
    """
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


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


def _with_doctype(body: str, doctype: str) -> str:
    """Return ``body`` prefixed with ``doctype`` unless it already carries one.

    ``generate_dita.py`` now emits the OASIS XML declaration + DOCTYPE into
    the source tree (so Oxygen recognises topics and maps). DITA-OT needs the
    same preamble, but prepending a second copy would yield two ``<?xml?>``
    lines and invalid XML — so inject only when the source lacks it. This
    keeps staging correct for both current and older DOCTYPE-less trees.
    """
    if body.lstrip().startswith("<?xml"):
        return body
    return doctype + body


def stage(src: Path, dst: Path) -> None:
    """Copy ``src`` to ``dst``, add DOCTYPEs, and tuck each ditamap inside
    its publication folder with hrefs rewritten relative to it.

    The source ``dita/`` tree keeps a single root with the ditamaps as
    siblings of the publication folders — that shape makes it easy for
    a human author to scan the corpus. But DITA-OT mirrors the topic
    paths it sees in the ditamap below the output directory, so a map
    at ``dita/progress-test-5.ditamap`` referencing
    ``progress-test-5/gram-01/gram_01.dita`` produces
    ``html/.../progress-test-5/progress-test-5/gram-01/gram_01.html``
    — a duplicated ``progress-test-5/`` segment that's visually
    confusing.

    Staging restructures the build-only copy so each ditamap lives at
    ``<staged>/<stem>/<stem>.ditamap`` with topic hrefs of the form
    ``<gram-folder>/<gram>.dita`` (no leading ``<stem>/``). DITA-OT
    then publishes into ``html/<edition>/<stem>/<gram-folder>/...``
    with no duplicated segment, and the original ``dita/`` tree is
    untouched.
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for path in dst.rglob("*.dita"):
        body = path.read_text(encoding="utf-8")
        _write_text(path, _with_doctype(body, TOPIC_DOCTYPE))
    for path in sorted(dst.glob("*.ditamap")):
        stem = path.stem
        body = path.read_text(encoding="utf-8")
        body = body.replace(f'href="{stem}/', 'href="')
        new_dir = dst / stem
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / path.name
        _write_text(new_path, _with_doctype(body, MAP_DOCTYPE))
        path.unlink()


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
        _write_text(path, prettify_html(original))
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


# -----------------------------------------------------------------------------
# GramFrame plugin integration
# -----------------------------------------------------------------------------
#
# The DITA source already emits each spectrogram as a ``<table class="gram-config">``
# carrying an ``<img colspan="2">`` plus the four parameter rows the
# GramFrame plugin expects (time-start, time-end, freq-start, freq-end).
# Loading ``gramframe.bundle.js`` on a page is therefore enough to upgrade
# every gram on it into an interactive viewer — see
# https://github.com/DeepBlueCLtd/GramFrame ``docs/HTML-Integration-Guide.md``.
#
# The bundle is vendored at ``vendor/gramframe/gramframe.bundle.js`` so
# air-gapped publish runs do not reach for the network. We copy it once
# to ``<out_root>/gramframe.bundle.js`` and inject a single relative
# ``<script>`` tag into every emitted page; the script no-ops on pages
# that have no ``gram-config`` tables.

GRAMFRAME_BUNDLE_SRC = Path(__file__).parent / "vendor" / "gramframe" / "gramframe.bundle.js"
GRAMFRAME_BUNDLE_NAME = "gramframe.bundle.js"

_GRAMFRAME_HEAD_CLOSE = "  </head>"


def inject_gramframe_plugin(
    out_root: Path,
    bundle_src: Path = GRAMFRAME_BUNDLE_SRC,
) -> int:
    """Copy the GramFrame bundle into ``out_root`` and link it from every page.

    Places one copy of the bundle at ``<out_root>/<GRAMFRAME_BUNDLE_NAME>``
    and inserts a ``<script src="…/gramframe.bundle.js" defer></script>``
    line into the ``<head>`` of every ``*.html`` file under ``out_root``,
    with the ``src`` written as a path relative to that file's parent
    directory (so ``file://`` browsing works).

    Idempotent: pages that already carry the tag are left alone, so
    re-running the publisher does not duplicate the tag and preserves
    byte-determinism.

    Returns the number of HTML files that received the tag on this call.
    """
    if not bundle_src.is_file():
        raise FileNotFoundError(
            f"GramFrame bundle missing at {bundle_src}. "
            "Vendor the v0.1.9 release asset before publishing."
        )
    bundle_dest = out_root / GRAMFRAME_BUNDLE_NAME
    bundle_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle_src, bundle_dest)

    count = 0
    for path in sorted(out_root.rglob("*.html")):
        body = path.read_text(encoding="utf-8")
        if GRAMFRAME_BUNDLE_NAME in body:
            continue
        rel = os.path.relpath(bundle_dest, start=path.parent).replace(os.sep, "/")
        tag = f'    <script src="{rel}" defer></script>\n{_GRAMFRAME_HEAD_CLOSE}'
        new_body, replaced = re.subn(
            re.escape(_GRAMFRAME_HEAD_CLOSE), tag, body, count=1,
        )
        if replaced:
            _write_text(path, new_body)
            count += 1
    return count


# -----------------------------------------------------------------------------
# Operator Console v2 dark theme
# -----------------------------------------------------------------------------
#
# A single ``theme.css`` (vendored from the design mockups under
# ``mockups/index-dark/``) drives every page type. The theme itself
# detects edition and page type from elements DITA-OT already emits
# (``ul.map`` for index pages, ``.ph`` for instructor edition); the
# attributes this module sets on ``<body>`` are belt-and-braces — kept
# so dev-side tooling (grep, dev-tools) can spot the page type at a
# glance, but the CSS no longer depends on them. The air-gapped Oxygen
# publish, which doesn't run this module, gets the same styling for
# free via the ``:has()``-based selectors in ``theme.css``.
#
# - ``data-edition="instructor"`` / ``"student"`` — informational; the
#   CSS detects edition via ``body:has(.ph)`` / ``body:not(:has(.ph))``.
# - ``class="ditamap-index"`` — informational; the CSS detects index
#   pages via ``body:has(ul.map)``.
# - ``class="edition-index"`` is the per-edition "choose a publication"
#   index (``<edition>/index.html``, written by ``write_edition_index``).
# - ``class="landing"`` is the shared top-level entry point
#   (``html/index.html``, written by ``write_shared_landing``).
#
# Topic gram pages carry only ``data-edition``.

THEME_BUNDLE_SRC = Path(__file__).parent / "vendor" / "themes" / "operator-console-v2" / "theme.css"
THEME_BUNDLE_NAME = "theme.css"

_HEAD_CLOSE = "  </head>"
# Matches any ``<link rel="stylesheet" … href="…/theme.css">`` line, so the
# idempotency check works regardless of the relative-path depth in the href.
_THEME_LINK_RE = re.compile(r'<link\b[^>]*\bhref="[^"]*theme\.css"', re.IGNORECASE)


def _theme_link_for(file_path: Path, theme_dest: Path) -> str:
    rel = os.path.relpath(theme_dest, start=file_path.parent).replace(os.sep, "/")
    return f'    <link rel="stylesheet" type="text/css" href="{rel}">'


def _theme_classify_page(
    rel_path: tuple[str, ...], editions: tuple[Edition, ...],
) -> tuple[str | None, str | None]:
    """Return ``(edition, body_class)`` for an HTML file under ``out_root``.

    ``rel_path`` is the file's path tuple relative to ``out_root``.

    - ``("index.html",)`` → shared landing, no edition, class ``landing``.
    - ``("<edition>", "index.html")`` → per-edition index, class ``edition-index``.
    - ``("<edition>", "<pub>", "index.html")`` → DITA-OT map index, class ``ditamap-index``.
    - Anything deeper under ``<edition>/`` → topic page, no special class.
    """
    edition_names = {e.output_subdir for e in editions}
    if len(rel_path) == 1 and rel_path[0] == "index.html":
        return None, "landing"
    if len(rel_path) >= 1 and rel_path[0] in edition_names:
        edition = rel_path[0]
        if len(rel_path) == 2 and rel_path[1] == "index.html":
            return edition, "edition-index"
        if len(rel_path) == 3 and rel_path[2] == "index.html":
            return edition, "ditamap-index"
        return edition, None
    return None, None


def inject_operator_console_theme(
    out_root: Path,
    editions: tuple[Edition, ...] = EDITIONS,
    bundle_src: Path = THEME_BUNDLE_SRC,
) -> int:
    """Vendor ``theme.css`` into ``out_root`` and link it from every page.

    Drops one copy of the theme at ``<out_root>/theme.css`` (so the
    shared landing can link it) and another copy at
    ``<out_root>/<edition>/theme.css`` for each edition (so per-edition
    index + every DITA-OT map index + every topic page can link a
    nearby copy with a short relative href).

    For each ``*.html`` under ``out_root``, ensures a
    ``<link rel="stylesheet" type="text/css" href="…/theme.css">`` sits
    in ``<head>``. Also stamps ``data-edition`` and page-type classes
    on ``<body>``; the CSS no longer requires these (it detects edition
    and page type via ``:has()`` against elements DITA-OT emits), but
    the attributes remain useful for dev-side inspection and testing.

    Idempotent: pages that already carry the theme link are left
    alone, preserving byte-determinism across re-runs.

    Returns the count of HTML files modified.
    """
    if not bundle_src.is_file():
        raise FileNotFoundError(
            f"Operator Console v2 theme bundle missing at {bundle_src}."
        )
    out_root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle_src, out_root / THEME_BUNDLE_NAME)
    for edition in editions:
        edition_dir = out_root / edition.output_subdir
        edition_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundle_src, edition_dir / THEME_BUNDLE_NAME)

    edition_themes: dict[str, Path] = {
        e.output_subdir: out_root / e.output_subdir / THEME_BUNDLE_NAME
        for e in editions
    }
    root_theme = out_root / THEME_BUNDLE_NAME

    count = 0
    for path in sorted(out_root.rglob("*.html")):
        rel_parts = path.relative_to(out_root).parts
        edition, page_class = _theme_classify_page(rel_parts, editions)

        theme_dest = (
            edition_themes[edition] if edition is not None else root_theme
        )
        body = path.read_text(encoding="utf-8")

        changed = False

        if _THEME_LINK_RE.search(body) is None:
            link_tag = _theme_link_for(path, theme_dest)
            inserted = f"{link_tag}\n{_HEAD_CLOSE}"
            new_body, replaced = re.subn(
                re.escape(_HEAD_CLOSE), inserted, body, count=1,
            )
            if replaced:
                body = new_body
                changed = True

        body, body_changed = _set_body_attrs(body, edition, page_class)
        if body_changed:
            changed = True

        if changed:
            _write_text(path, body)
            count += 1
    return count


_BODY_OPEN_RE = re.compile(r"<body(\s[^>]*)?>", re.IGNORECASE)


def _set_body_attrs(
    body: str, edition: str | None, page_class: str | None,
) -> tuple[str, bool]:
    """Set ``data-edition`` and append a page-type class on the ``<body>`` tag.

    Returns ``(new_body, changed)``. Existing attributes are preserved;
    when ``page_class`` is set and ``class`` already exists, the new
    token is appended unless already present.
    """
    match = _BODY_OPEN_RE.search(body)
    if match is None:
        return body, False
    attrs = match.group(1) or ""
    new_attrs = attrs
    changed = False

    if edition is not None and 'data-edition=' not in attrs:
        new_attrs = f'{new_attrs} data-edition="{edition}"'
        changed = True

    if page_class is not None:
        class_match = re.search(r'\bclass="([^"]*)"', new_attrs)
        if class_match is None:
            new_attrs = f'{new_attrs} class="{page_class}"'
            changed = True
        elif page_class not in class_match.group(1).split():
            existing = class_match.group(1)
            replacement = f'class="{existing} {page_class}"'
            new_attrs = new_attrs.replace(class_match.group(0), replacement, 1)
            changed = True

    if not changed:
        return body, False
    return body[:match.start()] + f"<body{new_attrs}>" + body[match.end():], True


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
            _write_text(path, scrubbed)
        count += 1
    return count


import xml.etree.ElementTree as _ET

_LEGACY_TITLE_ATTR_RE = re.compile(r'<map[^>]*\btitle="([^"]*)"', re.IGNORECASE)


def _ditamap_title(ditamap: Path, edition: "Edition | None" = None) -> str:
    """Return the human-readable map title for ``ditamap`` for ``edition``.

    Spec 003 ditamaps use a ``<title>`` child element of ``<map>``
    (replaces the legacy ``title=`` attribute) so the title can carry
    an audience-tagged ``<ph audience="-trainee">`` suffix. When
    ``edition`` is the student edition (its ``ditaval`` is set), every
    such ``<ph>`` is stripped from the title to match what the trainee
    filter renders in the per-page chrome. For the instructor edition
    (or when ``edition`` is None) the full title is returned.

    Falls back to the legacy ``title="..."`` attribute on ``<map>`` (no
    audience handling) if the ditamap doesn't carry a ``<title>``
    child, and finally to the ditamap stem if neither is present.
    """
    text = ditamap.read_text(encoding="utf-8")
    try:
        root = _ET.fromstring(text)
    except _ET.ParseError:
        return ditamap.stem

    title_el = root.find("title")
    if title_el is not None:
        strip_trainee = edition is not None and edition.ditaval is not None
        parts: list[str] = []
        if title_el.text:
            parts.append(title_el.text)
        for child in title_el:
            if (strip_trainee and child.tag == "ph"
                    and child.get("audience") == "-trainee"):
                # Audience filter excludes this element entirely.
                pass
            else:
                parts.append("".join(child.itertext()))
            if child.tail:
                parts.append(child.tail)
        return "".join(parts).strip()

    legacy = _LEGACY_TITLE_ATTR_RE.search(text)
    if legacy:
        return legacy.group(1)
    return ditamap.stem


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def _generated_timestamp() -> str:
    """Return a generation timestamp suitable for the landing-page chrome.

    Honours ``SOURCE_DATE_EPOCH`` for byte-deterministic output across
    runs (research R6 / FR-008 / SC-006). When the variable is absent
    or unparseable, falls back to the current UTC time so the landing
    page always shows a real timestamp; this trades byte-determinism
    for a readable preview, and CI/test runs that need determinism are
    expected to set ``SOURCE_DATE_EPOCH`` explicitly.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            ts = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
            return ts.strftime("%Y-%m-%d %H:%M UTC")
        except (TypeError, ValueError):
            pass
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


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
        f'        <li><a href="{_escape(href)}/index.html">{_escape(title)}</a></li>'
        for title, href in entries
    )
    edition_name = edition.name.title()
    out_subdir.mkdir(parents=True, exist_ok=True)
    index_path = out_subdir / "index.html"
    _write_text(
        index_path,
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '  <head>\n'
        '    <meta charset="UTF-8">\n'
        f'    <title>{edition_name} edition — published DITA output</title>\n'
        '  </head>\n'
        '  <body>\n'
        '    <main role="main">\n'
        f'      <h1>{edition_name} edition</h1>\n'
        f'      <p class="generated">Generated {generated_at}</p>\n'
        '      <ul class="deliverables">\n'
        f'{items}\n'
        '      </ul>\n'
        '    </main>\n'
        '  </body>\n'
        '</html>\n',
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
        f'        <li>\n'
        f'          <a href="{_escape(ed.output_subdir)}/index.html">'
        f'<strong>{_escape(ed.name.title())} edition</strong></a>\n'
        f'          <span class="meta">{_escape(ed.description)}</span>\n'
        f'        </li>'
        for ed in editions
    )
    out_root.mkdir(parents=True, exist_ok=True)
    index_path = out_root / "index.html"
    _write_text(
        index_path,
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '  <head>\n'
        '    <meta charset="UTF-8">\n'
        '    <title>Published DITA output — choose an edition</title>\n'
        '  </head>\n'
        '  <body>\n'
        '    <main role="main">\n'
        '      <h1>Published DITA output</h1>\n'
        f'      <p class="generated">Generated {generated_at}</p>\n'
        '      <ul class="deliverables">\n'
        f'{items}\n'
        '      </ul>\n'
        '    </main>\n'
        '  </body>\n'
        '</html>\n',
    )
    return index_path


def _dita_launcher(dita_ot: Path) -> Path:
    """Return the platform-appropriate DITA-OT launcher under ``dita_ot/bin``.

    DITA-OT ships two launchers side by side: an extensionless POSIX
    shell script (``bin/dita``) and a Windows batch wrapper
    (``bin/dita.bat``). Handing the shell script to ``CreateProcess`` on
    Windows fails with ``OSError: [WinError 193] %1 is not a valid Win32
    application`` because it is not a PE binary — the ``.bat`` wrapper
    must be used there instead. Selecting on ``os.name`` keeps one code
    path working on both the POSIX dev host and the air-gapped WinPython
    target.
    """
    name = "dita.bat" if os.name == "nt" else "dita"
    return dita_ot / "bin" / name


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
        str(_dita_launcher(dita_ot)),
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
    ditamaps = sorted(staged.glob("*/*.ditamap"))
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
    if not _dita_launcher(args.dita_ot).exists():
        print(f"DITA-OT not found at {args.dita_ot}", file=sys.stderr)
        return 1

    print(f"[stage] {args.dita} -> {args.staged}")
    stage(args.dita, args.staged)

    if args.out.exists():
        shutil.rmtree(args.out)
    args.out.mkdir(parents=True)
    rc = publish(args.dita_ot, args.staged, args.out)

    if rc == 0:
        ditamaps = sorted(args.staged.glob("*/*.ditamap"))
        generated_at = _generated_timestamp()
        for edition in EDITIONS:
            entries = [(_ditamap_title(m, edition), m.stem) for m in ditamaps]
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
        injected = inject_gramframe_plugin(args.out)
        print(
            f"[gramframe] vendored {GRAMFRAME_BUNDLE_NAME} into {args.out} "
            f"and linked it from {injected} HTML file(s)"
        )
        themed = inject_operator_console_theme(args.out)
        print(
            f"[theme] vendored {THEME_BUNDLE_NAME} (Operator Console v2) "
            f"and linked it from {themed} HTML file(s)"
        )

    shutil.rmtree(args.staged, ignore_errors=True)
    return rc


if __name__ == "__main__":
    rc = main()
    # Preserve CLI exit codes when invoked as a script, but stay silent
    # when invoked from an interactive REPL via runpy.run_path —
    # ``sys.exit`` would otherwise kill the interpreter and break the
    # up-arrow iteration loop. ``sys.ps1`` is only defined in
    # interactive sessions.
    if rc and not hasattr(sys, "ps1"):
        sys.exit(rc)

"""Drift guard for the gram-page layout CSS carried by the Oxygen head fragment.

The layout rules that give a gram page its full-width content column and its
floating link panels live in two standalone stylesheets under ``theme/``, each
of which needs its own ``.opt`` ``<resources>`` entry to reach the published
output.  On the air-gapped target only the GramFrame *head fragment* was ever
wired into the publishing template, so the grams went interactive while the
layout rules never arrived — the "On this page" mini-TOC kept reserving a
full-height right-hand column, squeezing the gramframe out of the page width.

The fragment therefore inlines those rules, so installing the one file that is
already wired installs the layout too.  Two copies of anything drift, so this
module asserts they stay in step: the fragment's ``<style>`` must carry each
stylesheet's rules verbatim, comments aside.

Standard library only, per the air-gapped test contract.
"""
from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THEME = REPO_ROOT / "theme"
FRAGMENT = (
    THEME / "gramframe-oxygen" / "page-templates-fragments" / "libraries"
    / "gramframe.xml"
)
SOURCES = (
    THEME / "gram-nav-panel" / "resources" / "gram-nav.css",
    THEME / "gram-toc-overlay" / "resources" / "gram-toc-overlay.css",
    THEME / "gram-fill-width" / "resources" / "gram-fill-width.css",
)

# The gramframe bundle's own styles top out here; anything meant to float OVER
# a gram has to clear it. Kept as a named constant so the reason survives.
GRAMFRAME_MAX_Z_INDEX = 1000


def _rules(css: str) -> str:
    """Reduce a stylesheet to its rules: comments and blank lines dropped.

    The standalone files carry long explanatory headers (the air-gapped
    debugging surface); the fragment carries only short pointers back to
    them.  Comparing rules-only lets each keep the prose that suits it while
    still failing the moment a declaration diverges.
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return "\n".join(line.rstrip() for line in css.splitlines() if line.strip())


def _fragment_style() -> str:
    """The text of the fragment's single ``<style>`` element."""
    root = ET.parse(FRAGMENT).getroot()
    styles = root.findall("style")
    assert len(styles) == 1, f"expected exactly one <style>, found {len(styles)}"
    return styles[0].text or ""


class ThemeHeadFragmentTests(unittest.TestCase):
    def test_fragment_is_well_formed_xml(self) -> None:
        """Oxygen fails the whole publish on a malformed fragment."""
        root = ET.parse(FRAGMENT).getroot()
        self.assertEqual(root.tag, "head")

    def test_fragment_still_loads_the_gramframe_bundle(self) -> None:
        """The CSS rides along with the script; it must not displace it."""
        root = ET.parse(FRAGMENT).getroot()
        srcs = [s.get("src", "") for s in root.findall("script")]
        self.assertTrue(
            any(src.endswith("gramframe.bundle.js"
                             "?buildId=${oxygen-webhelp-build-number}")
                for src in srcs),
            f"gramframe.bundle.js script tag missing or altered: {srcs}",
        )

    def test_inlined_css_matches_the_standalone_stylesheets(self) -> None:
        """Every rule in the standalone files is in the fragment, verbatim.

        Edit the stylesheet, copy the change into the fragment; this is what
        tells you when you forgot the second half.
        """
        inlined = _rules(_fragment_style())
        for source in SOURCES:
            with self.subTest(stylesheet=source.name):
                self.assertIn(
                    _rules(source.read_text(encoding="utf-8")),
                    inlined,
                    f"{source.name} has drifted from the copy inlined in "
                    f"{FRAGMENT.name}; re-copy its rules into the <style>.",
                )

    def test_inlined_css_carries_no_xml_hostile_characters(self) -> None:
        """``<`` or ``&`` in the CSS would need escaping to stay well-formed.

        They would then reach the browser as ``&lt;`` / ``&amp;`` inside the
        stylesheet, where CSS does no entity decoding.  Keeping them out of
        the rules altogether means the inlining stays a plain copy.
        """
        for source in SOURCES:
            with self.subTest(stylesheet=source.name):
                rules = _rules(source.read_text(encoding="utf-8"))
                self.assertNotIn("<", rules)
                self.assertNotIn("&", rules)

    def test_gram_page_scope_keys_off_both_markers(self) -> None:
        """The full-width rule must survive either marker going missing.

        ``p.gram-nav`` depends on Oxygen passing ``@outputclass`` through to
        ``@class``, which cannot be verified from the dev side of the air gap.
        ``.gram-frame-container`` is what gramframe.bundle.js wraps every
        upgraded gram in, so it is observable in the target's own browser.
        A page needing the full width is a page with a gram on it.
        """
        overlay = _rules(SOURCES[1].read_text(encoding="utf-8"))
        for selector in ("#wh_topic_body", "#wh_topic_toc"):
            with self.subTest(selector=selector):
                targeting = [
                    line for line in overlay.splitlines() if selector in line
                ]
                self.assertTrue(targeting, f"no rule targets {selector}")
                self.assertTrue(
                    any("body:has(p.gram-nav)" in line for line in targeting),
                    f"{selector} is not scoped by the DITA marker",
                )
                self.assertTrue(
                    any("body:has(.gram-frame-container)" in line
                        for line in targeting),
                    f"{selector} is not scoped by the rendered marker",
                )


    def test_floating_panels_stack_above_the_gramframe(self) -> None:
        """Both floating panels must outrank the gramframe's own z-indexes.

        They are pinned to the viewport and a full-width gram now runs under
        them, so a tie with the bundle's top layer (1000) would let the gram
        paint over the links on some pages and not others.
        """
        panels = {
            "gram-nav.css": SOURCES[0],
            "gram-toc-overlay.css": SOURCES[1],
        }
        for name, source in panels.items():
            with self.subTest(stylesheet=name):
                found = [
                    int(value)
                    for value in re.findall(
                        r"z-index:\s*(\d+)",
                        _rules(source.read_text(encoding="utf-8")),
                    )
                ]
                self.assertTrue(found, f"{name} declares no z-index")
                self.assertTrue(
                    all(z > GRAMFRAME_MAX_Z_INDEX for z in found),
                    f"{name} has a z-index at or below the gramframe's "
                    f"{GRAMFRAME_MAX_Z_INDEX}: {found}",
                )

    def test_gram_fills_its_column_width_over_the_inline_sizes(self) -> None:
        """The width fix has to beat the inline styles GramFrame re-applies.

        ``updateSVGLayout`` writes ``width``/``height`` straight onto the
        elements on every relayout, so only an important author declaration
        survives. ``height: auto`` is equally load-bearing: with the height
        pinned, ``preserveAspectRatio="xMidYMid meet"`` would letterbox the
        drawing instead of growing it, and ``screenToSVG`` would then scale
        cursor positions against a box the drawing no longer fills.
        """
        css = _rules(SOURCES[2].read_text(encoding="utf-8"))
        for declaration in (
            "width: 100% !important",
            "height: auto !important",
        ):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, css)
        self.assertIn(".gram-frame-container", css)
        self.assertIn("svg.gram-frame-svg", css)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

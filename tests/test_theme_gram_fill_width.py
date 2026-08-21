"""Contract for the full-width gram overlay.

``theme/gram-fill-width/`` makes each gram consume the width its column
offers, instead of rendering at the spectrogram's natural size and leaving a
band of whitespace either side.  It does that by overriding the inline sizes
GramFrame writes onto its own elements, which puts two easily-lost details
under test here.

Byte-identity between the overlay and the copy inside
``theme/pptx-transform/`` is *not* checked here — ``test_package_release.py``
already discovers and guards every template payload.  What that test cannot
see is whether the CSS still says the thing it has to say.

Standard library only, per the air-gapped test contract.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERLAY = REPO_ROOT / "theme" / "gram-fill-width" / "resources" / "gram-fill-width.css"
DEV_THEME = (
    REPO_ROOT / "scripts" / "vendor" / "themes" / "operator-console-v2" / "theme.css"
)
TEMPLATE_OPT = REPO_ROOT / "theme" / "pptx-transform" / "pptx-transform.opt"

# The gramframe bundle's own styles top out here; anything meant to float OVER
# a gram has to clear it. Kept as a named constant so the reason survives.
GRAMFRAME_MAX_Z_INDEX = 1000

FILL_RULES = (
    ".gram-frame-container {\n  width: 100% !important;\n}",
    "svg.gram-frame-svg {\n  width: 100% !important;\n  height: auto !important;\n"
    "  box-sizing: border-box;\n}",
)


def _rules(css: str) -> str:
    """Reduce a stylesheet to its rules: comments and blank lines dropped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return "\n".join(line.rstrip() for line in css.splitlines() if line.strip())


class GramFillWidthTests(unittest.TestCase):
    def test_overrides_beat_the_inline_sizes_gramframe_reapplies(self) -> None:
        """``!important`` and ``height: auto`` are both load-bearing.

        ``updateSVGLayout`` writes ``width``/``height`` straight onto the
        elements on every relayout, so only an important *author* declaration
        outranks them.  And with the height left pinned,
        ``preserveAspectRatio="xMidYMid meet"`` letterboxes the drawing rather
        than growing it — at which point ``screenToSVG``, which scales by
        ``viewBox.width / rect.width``, maps the cursor against a box the
        drawing no longer fills and the readouts go wrong.
        """
        css = _rules(OVERLAY.read_text(encoding="utf-8"))
        for rule in FILL_RULES:
            with self.subTest(rule=rule.splitlines()[0]):
                self.assertIn(rule, css)

    def test_dev_preview_theme_fills_the_gram_the_same_way(self) -> None:
        """The dev preview renders the same component, so it needs the same fix.

        ``publish_html.py`` injects the bundle into the preview too, so a gram
        there is the same natural-size component.  The repo's standing rule is
        that the Oxygen overlay and the operator-console theme stay visually in
        step; these rules involve no colours, so they are identical rather than
        merely equivalent.
        """
        dev = _rules(DEV_THEME.read_text(encoding="utf-8"))
        for rule in FILL_RULES:
            with self.subTest(rule=rule.splitlines()[0]):
                self.assertIn(
                    rule, dev,
                    "operator-console theme has drifted from "
                    "theme/gram-fill-width/; keep the preview in step.",
                )

    def test_dev_preview_gives_a_gram_page_room_to_fill(self) -> None:
        """A gram is ~971px natural; a 960px measure leaves nothing to fill.

        Without a wider gram page the preview cannot show the overlay working
        at all, which is how this went unnoticed in the first place.
        """
        dev = DEV_THEME.read_text(encoding="utf-8")
        match = re.search(
            r"body:has\(p\.gram-nav\) main\[role=\"main\"\] \{\s*max-width: (\d+)px",
            dev,
        )
        self.assertIsNotNone(match, "gram pages have no widened measure")
        self.assertGreater(int(match.group(1)), 1200)

    def test_template_wires_the_overlay(self) -> None:
        """A payload copied into the template but never referenced does nothing.

        test_package_release.py checks the copy is byte-identical to its
        overlay; it does not check the .opt actually loads it.
        """
        opt = TEMPLATE_OPT.read_text(encoding="utf-8")
        self.assertIn('<css file="resources/gram-fill-width.css"/>', opt)

    def test_floating_panel_stacks_above_the_gramframe(self) -> None:
        """The jump panel must outrank the gramframe's own z-indexes.

        It is pinned to the viewport and a full-width gram now runs under it,
        so a tie with the bundle's top layer would let the gram paint over the
        links on some pages and not others.
        """
        nav = REPO_ROOT / "theme" / "gram-nav-panel" / "resources" / "gram-nav.css"
        found = [
            int(v) for v in re.findall(r"z-index:\s*(\d+)",
                                       _rules(nav.read_text(encoding="utf-8")))
        ]
        self.assertTrue(found, "gram-nav.css declares no z-index")
        self.assertTrue(
            all(z > GRAMFRAME_MAX_Z_INDEX for z in found),
            f"gram-nav.css has a z-index at or below the gramframe's "
            f"{GRAMFRAME_MAX_Z_INDEX}: {found}",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

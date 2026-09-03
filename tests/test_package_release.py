"""Packaging contract for the GitHub-release deliverable zip.

Guards the air-gap transfer artifact built by
.github/scripts/package_release.py: the archive mirrors the target layout
(root scripts under scripts/, static/ and the loose operator files at the
root), carries nothing dev-host-only, and is byte-identical when rebuilt.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGER = REPO_ROOT / ".github" / "scripts" / "package_release.py"


def _load_packager():
    spec = importlib.util.spec_from_file_location("package_release", PACKAGER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(PACKAGER.is_file(), "packaging script not present in this tree")
class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_packager()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def _build(self, name):
        out = self.tmp / name
        self.module.build_zip(out, timestamp=1700000000)
        return out

    def test_archive_mirrors_target_layout(self):
        with zipfile.ZipFile(self._build("layout.zip")) as archive:
            names = set(archive.namelist())
        for canonical in (
            "deduplicate_csv.py",
            "extract_to_csv.py",
            "generate_dita.py",
            "introspect_pptx.py",
            "publish_html.py",
        ):
            self.assertIn("scripts/" + canonical, names)
        self.assertIn("static/welcome.dita", names)
        self.assertIn("static/security.dita", names)
        # The Oxygen GramFrame overlay travels under theme/ so the production
        # publisher on the air-gapped box can render interactive grams.
        self.assertIn(
            "theme/gramframe-oxygen/resources/gramframe.bundle.js", names)
        self.assertIn(
            "theme/gramframe-oxygen/page-templates-fragments/libraries/gramframe.xml",
            names)
        # The dark-mode overlay travels the same way: the operator installs it
        # into the Oxygen template so the production publish is dark with no
        # theme picker (issue #173).
        self.assertIn("theme/oxygen-dark-mode/resources/dark-mode.js", names)
        self.assertIn("theme/oxygen-dark-mode/resources/dark-mode.css", names)
        self.assertIn(
            "theme/oxygen-dark-mode/page-templates-fragments/libraries/dark-mode.xml",
            names)
        # The protective-marking overlay must reach the target too: without it
        # the operator's Oxygen publish is unmarked (issue #175).
        self.assertIn("theme/oxygen-protection/resources/protection.css", names)
        self.assertIn("theme/oxygen-protection/xslt/inc/customProtection.xsl", names)
        for fragment in ("protection-header.xml", "protection-footer.xml"):
            self.assertIn(
                "theme/oxygen-protection/page-templates-fragments/" + fragment,
                names)
        # ...as must the search-flag half of the same XSLT plumbing (issue #178).
        self.assertIn("theme/oxygen-hide-search/xslt/inc/customSearchFlag.xsl", names)
        self.assertIn(
            "theme/oxygen-hide-search/page-templates-fragments/search-flag.xml",
            names)
        self.assertIn("stock.wav", names)
        self.assertIn("requirements.txt", names)
        self.assertIn("README.md", names)
        # The wrapper templates (and the pipeline.py orchestrator) ship under
        # wrappers/, so an extract-over-ROOT\ upgrade delivers a new wrapper
        # without clobbering the operator's tuned root-level copies.
        for wrapper in ("extract.py", "dedupe.py", "write.py", "publish.py",
                        "introspect.py", "snapshot.py", "pipeline.py"):
            self.assertIn("wrappers/" + wrapper, names)

    def test_archive_carries_only_deliverables(self):
        with zipfile.ZipFile(self._build("only.zip")) as archive:
            names = archive.namelist()
        for name in names:
            allowed = (
                name.startswith("scripts/")
                or name.startswith("static/")
                or name.startswith("theme/")
                or name.startswith("wrappers/")
                or name in self.module.ROOT_FILES
            )
            self.assertTrue(allowed, f"unexpected archive entry: {name}")
        self.assertNotIn("run_pipeline.bat", names)
        # Dev-only mock tooling stays out of the deliverable.
        self.assertNotIn("scripts/generate_mock_analysis_sheet.py", names)
        # theme/ ships the overlays the operator installs, but not the
        # dev-host design-loop tooling that sits at its root.
        self.assertNotIn("theme/sync.py", names)
        self.assertFalse([n for n in names
                          if n.startswith("theme/") and n.endswith(".py")],
                         "theme/ python tooling must not ship")
        # The wrappers ship under wrappers/, never at the archive root, so an
        # extract-over-ROOT\ upgrade can't overwrite the operator's tuned copies.
        for wrapper in ("extract.py", "dedupe.py", "write.py",
                        "publish.py", "introspect.py", "snapshot.py",
                        "pipeline.py"):
            self.assertNotIn(wrapper, names)
            self.assertNotIn("scripts/" + wrapper, names)
        # vendor assets sit beside publish_html.py in the repo but are
        # not part of the archive contract.
        self.assertFalse(any(n.startswith("scripts/vendor/") for n in names),
                         "vendor assets must not ship in the archive")

    def test_theme_bundle_matches_vendored_bundle(self):
        # The GramFrame bundle the overlay ships must stay byte-identical to the
        # one publish_html.py vendors, so the production publish and the dev
        # preview render grams the same way.
        vendored = REPO_ROOT / "scripts" / "vendor" / "gramframe" / "gramframe.bundle.js"
        overlay = (REPO_ROOT / "theme" / "gramframe-oxygen" / "resources"
                   / "gramframe.bundle.js")
        self.assertTrue(vendored.is_file(), "vendored GramFrame bundle missing")
        self.assertTrue(overlay.is_file(), "overlay GramFrame bundle missing")
        self.assertEqual(
            vendored.read_bytes(), overlay.read_bytes(),
            "theme/ GramFrame bundle has drifted from scripts/vendor/gramframe/; "
            "update both copies (and their VERSION files) together")

    def test_publishing_template_payloads_match_their_overlays(self):
        # pptx-transform is a *wired* template: it carries a verbatim copy of
        # each overlay's payload rather than referencing it, because Oxygen
        # needs the files inside the template folder. Every copy is therefore a
        # drift point — and an overlay bumped on its own (a GramFrame upgrade, a
        # renamed marker class) silently leaves the template stale and wrong.
        #
        # Rather than list the payloads, discover them: any file under
        # pptx-transform/ whose name matches exactly one file in a sibling
        # overlay folder must be byte-identical to it. New overlays are then
        # covered the moment they are wired in, with no test edit.
        template = REPO_ROOT / "theme" / "pptx-transform"
        self.assertTrue(template.is_dir(), "pptx-transform template missing")

        sources = {}
        for overlay in sorted(REPO_ROOT.glob("theme/*")):
            if not overlay.is_dir() or overlay.name == "pptx-transform":
                continue
            for src in overlay.rglob("*"):
                if src.is_file() and src.name != "README.md":
                    sources.setdefault(src.name, []).append(src)

        checked = 0
        for copy in sorted(template.rglob("*")):
            if not copy.is_file():
                continue
            candidates = sources.get(copy.name)
            # Ambiguous or absent (VERSION lives in several overlays; the stock
            # Oxygen files have no overlay counterpart) — nothing to compare.
            if not candidates or len(candidates) > 1:
                continue
            src = candidates[0]
            checked += 1
            with self.subTest(payload=copy.name):
                self.assertEqual(
                    src.read_bytes(), copy.read_bytes(),
                    f"{copy.relative_to(REPO_ROOT)} has drifted from "
                    f"{src.relative_to(REPO_ROOT)}; re-copy it so the template "
                    "publishes what the overlay actually specifies")
        # Guard the guard: if the discovery ever matches nothing, this test
        # would pass vacuously while every payload silently rots.
        self.assertGreaterEqual(
            checked, 5,
            "expected to check at least the GramFrame bundle, hide-search, "
            f"gram-nav, gram-toc-overlay and dark-mode payloads; checked {checked}")

    def test_publishing_template_wires_the_overlays(self):
        # pptx-transform is the template the operator actually publishes with,
        # so it must carry both overlays wired in — not just the payload files.
        # A fragment under a bare <fragments>, or directly under <webhelp>,
        # fails the Oxygen publish with "Build failed with an exception: null".
        import xml.etree.ElementTree as ET

        opt = (REPO_ROOT / "theme" / "pptx-transform" / "pptx-transform.opt")
        self.assertTrue(opt.is_file(), "pptx-transform.opt missing")
        webhelp = ET.parse(opt).getroot().find("webhelp")

        # Stock default is "no", which leaves each week_N.dita page an empty
        # <h1> and its grams reachable only from the side TOC.
        params = {p.get("name"): p.get("value")
                  for p in webhelp.findall("parameters/parameter")}
        self.assertEqual(params.get("webhelp.show.child.links"), "yes")

        # Every overlay stylesheet must load AFTER all three stock ones, or the
        # stock rules win and the overlay silently does nothing.
        css = [c.get("file") for c in webhelp.findall("resources/css")]
        stock = ["oxygen-theme.css", "oxygen.css", "notes.css"]
        overlays = ["resources/hide-search.css", "resources/gram-nav.css",
                    "resources/gram-toc-overlay.css", "resources/dark-mode.css",
                    "resources/protection.css"]
        for name in stock + overlays:
            self.assertIn(name, css)
        self.assertLess(
            max(css.index(s) for s in stock),
            min(css.index(o) for o in overlays),
            "overlay CSS must come after the stock CSS to win the cascade")
        # A protective marking is the one thing no later stylesheet may repaint.
        self.assertEqual(
            css[-1], "resources/protection.css",
            "protection.css must load LAST so nothing can restyle the marking")

        # gramframe rides the topic-page head; dark-mode must ride the ALL-pages
        # head, or the welcome and search pages publish light. Oxygen binds one
        # fragment per placeholder, so they cannot share one.
        fragments = {f.get("file"): f.get("placeholder")
                     for f in webhelp.findall("html-fragments/fragment")}
        self.assertEqual(
            fragments.get("page-templates-fragments/libraries/gramframe.xml"),
            "webhelp.fragment.head.topic.page")
        self.assertEqual(
            fragments.get("page-templates-fragments/libraries/dark-mode.xml"),
            "webhelp.fragment.head")
        # The protective marking (#175) and the search flag (#178) ride three
        # body-level placeholders. All three must be bound, and bound to
        # placeholders that reach EVERY page type — issue #178 was precisely a
        # customization that reached only the pages built from a topic.
        self.assertEqual(
            fragments.get("page-templates-fragments/protection-header.xml"),
            "webhelp.fragment.before.body")
        self.assertEqual(
            fragments.get("page-templates-fragments/protection-footer.xml"),
            "webhelp.fragment.after.body")
        self.assertEqual(
            fragments.get("page-templates-fragments/search-flag.xml"),
            "webhelp.fragment.after.header")
        self.assertEqual(len(fragments), len(webhelp.findall("html-fragments/fragment")),
                         "two fragments share a file entry")
        self.assertEqual(
            len(set(fragments.values())), len(fragments),
            "Oxygen binds one fragment per placeholder; two share one")

        # Marking parameters (#175). The values are scenario-overridable, but
        # they must be DECLARED here or oxyf:getParameter has nothing to read.
        self.assertEqual(params.get("webhelp.show.protection"), "yes")
        self.assertTrue(
            (params.get("webhelp.protection.text") or "").strip(),
            "webhelp.protection.text must ship with a marking, not blank")
        self.assertIn("webhelp.protection.background.color", params,
                      "the per-export colour override must be declared")

        # Search visibility (#178) must NOT become a parameter of our own.
        # Operators rebuild scenarios from the stock built-in, and a parameter
        # they have to remember to re-add is one they will eventually forget —
        # silently, since a missing one just reads as empty. It is derived from
        # args.filter instead, which they cannot omit without the student build
        # coming out full of instructor content.
        self.assertNotIn(
            "webhelp.show.search", params,
            "derive search visibility from args.filter, not a parameter an "
            "operator must remember to set on a rebuilt scenario")

        # Every page type needs the customizations, so every page-type XSLT
        # extension point must be wired. Missing createMainPage is exactly how
        # index.html lost its search box in #178.
        extensions = {e.get("id"): e.get("file")
                      for e in webhelp.findall("xslt/extension")}
        for point in ("com.oxygenxml.webhelp.xsl.createMainPage",
                      "com.oxygenxml.webhelp.xsl.dita2webhelp",
                      "com.oxygenxml.webhelp.xsl.createSearchPage",
                      "com.oxygenxml.webhelp.xsl.createIndexTermsPage"):
            self.assertIn(point, extensions,
                          f"{point} unwired: that page type publishes unmarked")
        # ...and each of those stylesheets must actually pull in both includes.
        for stylesheet in extensions.values():
            source = (opt.parent / stylesheet).read_text(encoding="utf-8")
            with self.subTest(stylesheet=stylesheet):
                self.assertIn("inc/customProtection.xsl", source)
                self.assertIn("inc/customSearchFlag.xsl", source)

        # The dark-mode overlay is verified against enable.dark.mode=yes; "no"
        # switches off Oxygen's dark plumbing entirely.
        self.assertEqual(params.get("webhelp.enable.dark.mode"), "yes")

        # Oxygen's schematron asserts every referenced file resolves on disk.
        for el in webhelp.iter():
            ref = el.get("file")
            if ref:
                self.assertTrue((opt.parent / ref).is_file(),
                                f"{el.tag} references missing file: {ref}")

    def test_marking_and_search_wiring_agrees_across_files(self):
        # The protective marking (#175) and the search flag (#178) are each
        # spread over three files that only agree by convention: a fragment
        # declares a placeholder class, an XSLT matches that class and reads
        # named parameters, and (for search) a CSS selects the class the XSLT
        # emits. Nothing in the toolchain complains when one of them is
        # renamed — the publish simply runs and the feature silently does
        # nothing. Neither can be caught by publishing locally either: the
        # WebHelp CLI needs a licence the project does not have, so this test
        # is the only automated guard between an edit and a manual Oxygen run.
        import re
        import xml.etree.ElementTree as ET

        template = REPO_ROOT / "theme" / "pptx-transform"
        opt = template / "pptx-transform.opt"
        webhelp = ET.parse(opt).getroot().find("webhelp")
        declared = {p.get("name") for p in webhelp.findall("parameters/parameter")}

        def read(rel):
            return (template / rel).read_text(encoding="utf-8")

        protection = read("xslt/inc/customProtection.xsl")
        search_flag = read("xslt/inc/customSearchFlag.xsl")

        # 1. Placeholder classes: what the fragment declares is what the XSLT
        #    matches. A mismatch leaves the raw empty element in the output —
        #    an unfilled bar or a dead flag.
        for fragment, klass, xslt in (
            ("page-templates-fragments/protection-header.xml",
             "wh_header_protection", protection),
            ("page-templates-fragments/protection-footer.xml",
             "wh_footer_protection", protection),
            ("page-templates-fragments/search-flag.xml",
             "wh_search_visibility", search_flag),
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(f'class="{klass}"', read(fragment))
                self.assertIn(f"'{klass}'", xslt,
                              f"no XSLT template matches {klass}")

        # 2. Fragment shape. Oxygen's includeCustomHTMLContent copies only
        #    <body>'s children when it finds an <html>/<body> wrapper, and the
        #    WHOLE document — explanatory comments and all — when it does not.
        #    Drop the wrapper and every published page grows a block comment.
        for fragment in ("page-templates-fragments/protection-header.xml",
                         "page-templates-fragments/protection-footer.xml",
                         "page-templates-fragments/search-flag.xml"):
            with self.subTest(fragment=fragment):
                root = ET.parse(template / fragment).getroot()
                self.assertEqual(root.tag, "{http://www.w3.org/1999/xhtml}html")
                self.assertEqual(
                    [child.tag for child in root],
                    ["{http://www.w3.org/1999/xhtml}body"],
                    "the placeholder must sit inside a <body> wrapper")

        # 3. Every parameter the XSLT reads is one it can actually get a value
        #    for. An undeclared one reads as empty, which for show.protection
        #    would mean silently no marking at all.
        #
        #    DITA-OT's own build properties are readable too — Oxygen's
        #    whr-create-props-file serialises every Ant property — and are
        #    deliberately NOT declared in the .opt, because declaring them would
        #    override what the scenario set. args.filter is the search flag's
        #    whole mechanism (#178), so allow it by name rather than loosening
        #    the check.
        dita_ot_supplied = {"args.filter"}
        for xslt, name in ((protection, "customProtection.xsl"),
                           (search_flag, "customSearchFlag.xsl")):
            used = set(re.findall(r"oxyf:getParameter\('([^']+)'\)", xslt))
            self.assertTrue(used, f"{name} reads no parameters at all")
            with self.subTest(xslt=name):
                self.assertLessEqual(
                    used, declared | dita_ot_supplied,
                    f"{name} reads parameters that are neither declared in the "
                    f".opt nor supplied by DITA-OT: "
                    f"{sorted(used - declared - dita_ot_supplied)}")
        # The search flag must key off the DITAVAL, not a parameter of its own.
        self.assertIn(
            "args.filter", search_flag,
            "customSearchFlag.xsl must derive the edition from args.filter")
        # ...and off what that DITAVAL DOES, not its filename. Matching the name
        # `trainee.ditaval` was tried and failed in a real publish: DITA-OT's
        # preprocess merges the filter into <temp>/ditaot.generated.ditaval, so
        # by page-generation time the name is not ours.
        self.assertIn(
            "'-trainee'", search_flag,
            "identify the student edition by the audience its DITAVAL excludes")
        # The header comment documents the rejected filename approach, so look
        # only at live markup.
        live_search_flag = re.sub(r"<!--.*?-->", "", search_flag, flags=re.DOTALL)
        self.assertNotIn(
            "trainee.ditaval", live_search_flag,
            "matching the DITAVAL filename breaks once DITA-OT merges it into "
            "ditaot.generated.ditaval; test what the DITAVAL excludes instead")

        # 5. Both marker classes are emitted, and only the student one is
        #    styled. This mechanism runs ONLY inside a real Oxygen publish, so
        #    the instructor marker is what makes "the fragment arrived and chose
        #    to show" distinguishable from "the fragment never arrived" in a
        #    published page. Dropping it costs a diagnosis cycle, not a feature.
        hide_css = read("resources/hide-search.css")
        for marker in ("wh-search-hidden", "wh-search-shown"):
            with self.subTest(marker=marker):
                self.assertIn(marker, live_search_flag,
                              f"{marker} must be emitted so a publish can be "
                              "checked by grepping a page")
        live_hide_css = re.sub(r"/\*.*?\*/", "", hide_css, flags=re.DOTALL)
        self.assertIn("wh-search-hidden", live_hide_css)
        self.assertNotIn(
            "wh-search-shown", live_hide_css,
            "the instructor marker is a diagnostic, not a style hook; giving "
            "it a rule would make it load-bearing")

        # 4. The old content-inferred rule is what #178 was: it hid the box
        # wherever the instructor marker was absent, which on index.html and
        # search.html is BOTH editions. It must not creep back — as a live
        # rule. The stylesheet quotes it in a comment explaining the fix, so
        # strip comments before looking.
        live_css = re.sub(r"/\*.*?\*/", "", read("resources/hide-search.css"),
                          flags=re.DOTALL)
        self.assertNotIn(
            ":not(:has(.gf-persistent))", live_css,
            "the marker-absence rule hides search on the instructor's own "
            "landing page; hide only where the student is positively flagged")

    def test_rebuild_is_byte_identical(self):
        first = self._build("first.zip")
        second = self._build("second.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()

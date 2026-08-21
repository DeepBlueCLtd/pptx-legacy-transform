<?xml version="1.0" encoding="UTF-8"?>
<!--
    Customizations for the SEARCH RESULTS page extension point,
    com.oxygenxml.webhelp.xsl.createSearchPage.

    Oxygen exposes one XSLT extension point per generated page type, and a
    customization only reaches the pages whose extension point imports it. The
    two overlays wired below must reach EVERY page - a protective marking that
    is missing from one page is not a marking, and issue #178 was precisely a
    customization that failed to reach index.html and search.html - so all four
    extension points import the same pair of includes, and these four files are
    deliberately identical apart from this comment. Change one, change all four.

      xslt/inc/customProtection.xsl   theme/oxygen-protection  (issue #175)
      xslt/inc/customSearchFlag.xsl   theme/oxygen-hide-search (issue #178)

    Both are verbatim copies of their overlay's source; the three files these
    stylesheets import them from are template wiring and have no overlay
    counterpart, which is why tests/test_package_release.py's payload-drift
    check skips them and checks the includes instead.

    NOTE: do NOT override <whc:page_libraries> here. Fi3ldMan's Oxygen 2024
    template did, injecting a hard-coded list of Oxygen's own CSS/JS bundles,
    and that is what broke its output under Oxygen 2026. Custom scripts belong
    in an <html-fragments> entry - see the gramframe and dark-mode fragments in
    pptx-transform.opt.
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:whc="http://www.oxygenxml.com/webhelp/components"
    xmlns:oxyf="http://www.oxygenxml.com/functions"
    exclude-result-prefixes="#all" version="2.0">

    <xsl:import href="inc/customProtection.xsl"/>
    <xsl:import href="inc/customSearchFlag.xsl"/>

</xsl:stylesheet>

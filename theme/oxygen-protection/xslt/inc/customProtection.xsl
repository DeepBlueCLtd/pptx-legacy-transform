<?xml version="1.0" encoding="UTF-8"?>
<!--
    Protective marking bars for the Oxygen WebHelp Responsive output (issue #175).

    Fills in the two empty placeholder elements declared by this overlay's
    page-templates-fragments/protection-header.xml and protection-footer.xml,
    which the publishing template binds to the `webhelp.fragment.before.body`
    and `webhelp.fragment.after.body` extension points. Both placeholders reach
    EVERY generated page type - main/tiles, topic, search results and index
    terms - so the marking cannot be missing from a page.

    Driven by three custom parameters declared in the template `.opt` and
    overridable per transformation scenario:

      webhelp.show.protection             yes | no   (anything but "yes" = no bars)
      webhelp.protection.text             the marking, e.g. COMMERCIALLY SENSITIVE
      webhelp.protection.background.color optional override; empty = the colour
                                          pinned in resources/protection.css

    WHY parameters rather than literal markup: the delivered target sits behind
    a one-way air-gap gateway. Editing CSS, XSLT or the `.opt` costs a full
    template re-transfer; changing a scenario parameter costs nothing, because
    the scenario lives on the target. So the marking - the one thing that
    plausibly changes per export - is a parameter.

    Fragment content included via <whc:include_html> is re-processed in
    `copy_template` mode by Oxygen's own commonComponentsExpander.xsl (see
    `includeCustomHTMLContent`), which is what lets these templates match
    inside a fragment file rather than a forked page layout.

    Ported from C:\git\Fi3ldMan\dita-parent\pub-5\template-2026\xslt\inc\, with
    one deliberate divergence: Fi3ldMan forks all four wt_*.html page layouts
    plus header.xml/footer.xml to host its placeholders, and pays the cost of
    re-diffing them against stock on every Oxygen upgrade. Binding to the
    before.body / after.body fragment points instead keeps this template
    stock-plus-parameters, with no forked page layouts to maintain.
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:whc="http://www.oxygenxml.com/webhelp/components"
    xmlns:oxyf="http://www.oxygenxml.com/functions"
    exclude-result-prefixes="#all" version="2.0">

    <!-- The top bar, from page-templates-fragments/protection-header.xml. -->
    <xsl:template match="*:header[contains(@class, 'wh_header_protection')]" mode="copy_template">
        <xsl:if test="oxyf:getParameter('webhelp.show.protection') = 'yes'">
            <xsl:copy>
                <xsl:copy-of select="@*"/>
                <xsl:call-template name="protection-background-colour"/>
                <div class="header-container mx-auto">
                    <xsl:value-of select="oxyf:getParameter('webhelp.protection.text')"/>
                </div>
            </xsl:copy>
        </xsl:if>
    </xsl:template>

    <!-- The bottom bar, from page-templates-fragments/protection-footer.xml. -->
    <xsl:template match="*:footer[contains(@class, 'wh_footer_protection')]" mode="copy_template">
        <xsl:if test="oxyf:getParameter('webhelp.show.protection') = 'yes'">
            <xsl:copy>
                <xsl:copy-of select="@*"/>
                <xsl:call-template name="protection-background-colour"/>
                <div class="footer-container mx-auto">
                    <span>
                        <xsl:value-of select="oxyf:getParameter('webhelp.protection.text')"/>
                    </span>
                </div>
            </xsl:copy>
        </xsl:if>
    </xsl:template>

    <!--
        Emit a @style background-color ONLY when the scenario overrides it.
        Left empty (the shipped default), the bar takes the single fixed colour
        pinned in resources/protection.css - the same in light and dark mode.
    -->
    <xsl:template name="protection-background-colour">
        <xsl:if test="oxyf:getParameter('webhelp.protection.background.color') != ''">
            <xsl:attribute name="style">
                <xsl:text>background-color:</xsl:text>
                <xsl:value-of select="oxyf:getParameter('webhelp.protection.background.color')"/>
            </xsl:attribute>
        </xsl:if>
    </xsl:template>

</xsl:stylesheet>

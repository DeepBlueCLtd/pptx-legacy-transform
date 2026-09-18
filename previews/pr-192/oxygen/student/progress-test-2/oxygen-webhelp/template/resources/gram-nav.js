/* Move the per-gram jump links into the WebHelp toolbar (issue #179).
 *
 * generate_dita.py emits one <p outputclass="gram-nav"> per gram page, holding
 * one in-page link per content section — 7 Questions (student edition),
 * Lofar N / WAV N / Demon N (both), Analysis Sheet (instructor edition) — in
 * page order. Oxygen renders it where the DITA puts it, at the foot of the
 * article. This script relocates it into <nav class="wh_tools">, the toolbar
 * that already carries the maximise, collapse and print buttons, so the links
 * are always on screen and steal no width from the gramframe.
 *
 * WHY A SCRIPT AND NOT CSS. The paragraph and the toolbar are in different
 * subtrees of the page (the toolbar is in #wh_topic_container's first row, the
 * paragraph is inside .wh_content_area), and CSS cannot reparent an element.
 * Absolutely positioning the paragraph over the toolbar instead would have to
 * guess the bar's height and margins and would collide with the button cluster
 * as soon as the links wrapped. Ten lines of DOM move is the honest version.
 *
 * WHY IT MARKS THE NODES. resources/gram-nav.css hangs every rule off the two
 * classes stamped below rather than on `nav.wh_tools`. That keeps the styling —
 * the sticky row in particular — on gram pages only: the welcome, security,
 * week and publication index pages have no gram-nav paragraph, this script
 * returns early there, and their toolbars keep the stock behaviour. It also
 * avoids needing :has() to express "a toolbar that contains jump links".
 *
 * Insertion point is *before* .wh_right_tools, so the links take the empty
 * middle of the bar and the buttons stay hard right where readers expect them.
 *
 * Load it from an <html-fragments> entry bound to
 * webhelp.fragment.after.body.topic.page — the end of <body> on topic pages,
 * which is where the elements it needs already exist, and one of the few
 * placeholders this template has not already spent (see pptx-transform.opt).
 * No `defer`: the fragment is the last thing in <body>, so the DOM below it is
 * parsed and the move happens before the first paint, with no flash of the
 * paragraph in its old position.
 */
(function () {
    "use strict";

    var nav = document.querySelector("p.gram-nav");
    var tools = document.querySelector("nav.wh_tools");
    if (!nav || !tools) {
        /* Not a gram page, or a page type with no toolbar. Nothing to do. */
        return;
    }

    tools.insertBefore(nav, tools.querySelector(".wh_right_tools"));
    tools.classList.add("wh_tools_gram_nav");
    if (tools.parentNode && tools.parentNode.classList) {
        tools.parentNode.classList.add("wh_tools_row_gram_nav");
    }
})();

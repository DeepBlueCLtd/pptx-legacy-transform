/* Move the WebHelp search box up into the header bar.
 *
 * Oxygen renders the search box as a full-width band BELOW the header:
 *
 *   <header class="navbar wh_header"> … title … top menu … </header>
 *   <div class="wh_search_input navbar-form … search"> <form id="searchForm"> …
 *
 * and the stock stylesheet gives that band `padding: 40px 0` plus a background
 * image (`115px 0` on the tiles landing page). So a control that is one input
 * tall costs ~120px of vertical space on every page — on a gram page, space
 * that belongs to the spectrogram.
 *
 * This relocates the band into the header's own flex container, beside the top
 * menu, in the slot the theme picker vacated (../oxygen-dark-mode/ hides it).
 * resources/search-in-header.css then strips the padding and background and
 * sizes it as an ordinary header control.
 *
 * WHY A SCRIPT AND NOT CSS. The band is a SIBLING of <header>, so no amount of
 * styling puts it inside: CSS cannot reparent an element. Absolutely
 * positioning it over the header instead would have to resolve against <body>
 * — the header is not the nearest positioned ancestor — and the protective
 * marking bar above it (../oxygen-protection/) makes the header's offset a
 * moving target. Reparenting is the honest version.
 *
 * WHY IT MARKS THE HEADER. search-in-header.css hangs every rule off the
 * `wh_header_search` class stamped below rather than on `.wh_search_input`, so
 * the compact styling applies only where the move actually happened. With
 * JavaScript off the band stays put and keeps its stock appearance, which is
 * merely the old layout, not a broken one.
 *
 * ALL PAGE TYPES. Bound to `webhelp.fragment.after.search.input`, which the
 * topic, tiles-landing and search-results templates all include (the index-
 * terms page has no search box, so there is nothing to move). The fragment
 * sits INSIDE the band, after the header markup, so both elements are parsed
 * by the time this runs — no defer, and the move happens before first paint.
 *
 * ORDERING MATTERS HERE, AND IT IS NOT OBVIOUS. This script runs from *inside*
 * the very element it moves, while the parser is still within that element.
 * That is safe only because `webhelp.fragment.after.search.input` comes AFTER
 * `whc:component_content` in every page template: the <form> is already parsed,
 * and all that follows is the sibling `…after.search.input.<page>` include and
 * the closing tags, which the parser goes on appending to the band in its new
 * home. Do NOT re-bind this to `webhelp.fragment.before.search.input` — there
 * the form does not exist yet, and the header would get an empty box.
 *
 * Student edition: ../oxygen-hide-search/ hides the band outright there, so
 * this leaves no empty control in the header.
 */
(function () {
    "use strict";

    var search = document.querySelector(".wh_search_input");
    var header = document.querySelector("header.wh_header");
    if (!search || !header) {
        /* A page type with no search box, or no header to move it into. */
        return;
    }

    /* Prefer the collapsible group that already holds the top menu, so the
       search sits with the navigation and collapses with it on a narrow
       screen. Fall back to the header's flex row if the template ever drops
       that wrapper. */
    var host = header.querySelector(".wh_top_menu_and_indexterms_link")
        || header.querySelector(".wh_header_flex_container");
    if (!host) {
        return;
    }

    host.appendChild(search);
    header.classList.add("wh_header_search");
})();

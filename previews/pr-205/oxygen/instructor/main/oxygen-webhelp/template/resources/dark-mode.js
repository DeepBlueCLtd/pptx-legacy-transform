/*
 * Force the Oxygen WebHelp Responsive dark theme (issue #173).
 *
 * Oxygen's stock themes.js decides the page theme at load time from the
 * reader's stored choice (localStorage) or, failing that, the browser's
 * prefers-color-scheme, and marks a dark page by setting
 * data-wh-theme="dark" on <html>. Light is the ABSENCE of that attribute —
 * themes.js only ever sets it, never removes it (only a click on the theme
 * menu removes it), so pinning the attribute here is stable no matter what
 * themes.js decided or what a reader chose on an earlier visit.
 *
 * Loaded from a <head> fragment WITHOUT defer/async so it runs before the
 * first paint — a deferred version would flash the light theme first.
 *
 * The companion dark-mode.css hides the theme menu, so nothing in the
 * published output can put the page back into light mode. See ../README.md.
 */
(function () {
    "use strict";
    var root = document.documentElement;
    if (root.getAttribute("data-wh-theme") !== "dark") {
        root.setAttribute("data-wh-theme", "dark");
    }
})();

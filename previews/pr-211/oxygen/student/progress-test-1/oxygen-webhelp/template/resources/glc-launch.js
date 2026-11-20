/* Open a gram's .glc in the legacy replay tool instead of showing it (issue #199).
 *
 * A WAV gram page links to its .glc config, which names the .wav beside it.
 * In the PowerPoint decks clicking that link launched the legacy replay tool;
 * in a browser it just displays the .glc as text. A browser will never hand a
 * file:// link to a desktop application, and downloading the .glc does not
 * help either: the .glc names its .wav by a path relative to ITSELF, so a copy
 * in the Downloads folder points at a .wav that is not there.
 *
 * So the .glc has to be opened WHERE IT IS PUBLISHED, by its full Windows path.
 * This script works that path out from the page's own location and offers two
 * ways to use it:
 *
 *   1. The link itself becomes  glc:<full path>  - a custom URL scheme that
 *      theme/glc-launch/client/ registers on each student PC. Windows hands the
 *      path to a launcher that opens it with whatever .glc is associated with:
 *      the replay tool.
 *   2. A "Copy path" button beside it, for a PC without the handler: paste the
 *      path into Win+R (or Explorer's address bar) and Windows opens it with
 *      the same association.
 *
 * Only pages opened from a drive or file share (file://) are upgraded. Served
 * over http(s) there is no Windows path to give the tool, so the link is left
 * exactly as published.
 *
 * Hooks are the DITA-source ones generate_dita.py emits: the link lives in a
 * section with outputclass="wav-stage", and its href ends in ".glc".
 */
(function () {
    "use strict";

    if (window.location.protocol !== "file:") {
        return;
    }

    /* file:///Z:/pubs/main/gram-03/x.glc      ->  Z:\pubs\main\gram-03\x.glc
       file://server/share/main/gram-03/x.glc  ->  \\server\share\main\gram-03\x.glc */
    function windowsPath(url) {
        var path = decodeURIComponent(url.pathname);
        if (url.host) {
            return "\\\\" + url.host + path.replace(/\//g, "\\");
        }
        return path.replace(/^\/([A-Za-z]:)/, "$1").replace(/\//g, "\\");
    }

    function copyText(text, done) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done, function () {
                copyFallback(text, done);
            });
            return;
        }
        copyFallback(text, done);
    }

    function copyFallback(text, done) {
        var area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        try {
            document.execCommand("copy");
            done();
        } catch (e) {
            /* Nothing more to try; the path is still on screen to select. */
        }
        document.body.removeChild(area);
    }

    function upgrade(link) {
        var target = new URL(link.getAttribute("href"), window.location.href);
        var path = windowsPath(target);

        /* Fully percent-encoded, so the launcher decodes exactly once and a
           space, '%' or '#' in a folder name survives the trip intact. */
        link.setAttribute("href", "glc:" + encodeURIComponent(path));
        link.setAttribute("title", "Open in the replay tool: " + path);
        link.classList.add("glc-launch");

        var button = document.createElement("button");
        button.type = "button";
        button.className = "glc-copy-path";
        button.textContent = "Copy path";
        button.title = "Copy the full path, then paste it into Win+R to open "
            + "the gram in the replay tool";
        button.addEventListener("click", function () {
            copyText(path, function () {
                button.textContent = "Copied";
                window.setTimeout(function () {
                    button.textContent = "Copy path";
                }, 2000);
            });
        });

        var shown = document.createElement("code");
        shown.className = "glc-path";
        shown.textContent = path;

        link.parentNode.insertBefore(shown, link.nextSibling);
        link.parentNode.insertBefore(button, link.nextSibling);
    }

    var links = document.querySelectorAll(".wav-stage a[href]");
    for (var i = 0; i < links.length; i++) {
        if (/\.glc$/i.test(links[i].getAttribute("href"))) {
            upgrade(links[i]);
        }
    }
})();

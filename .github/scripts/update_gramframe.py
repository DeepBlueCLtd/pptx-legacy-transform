#!/usr/bin/env python3
"""Refresh the vendored GramFrame bundle from its GitHub releases.

Dev-host and CI only: it needs the internet, so it lives here beside
``package_release.py`` rather than under ``scripts/`` and never reaches the
air-gapped target.  Stdlib only, and 3.9-safe, like everything else here.

WHY THE BUNDLE STAYS COMMITTED, AND IS NOT FETCHED AT PACKAGE TIME.  Pulling
the latest release while building the deliverable zip would break two things
that matter more than the convenience:

  * **Determinism.** ``tests/test_package_release.py`` rebuilds the archive and
    byte-compares it.  An artifact whose contents depend on what GramFrame
    published this morning cannot satisfy that, and the operator's ``.sha256``
    stops meaning anything.
  * **Testedness.** The bundle that reaches an air-gapped box should be the one
    the suite actually ran against — ``tests/test_theme_gram_fill_width.py``
    reads the bundle's own z-index ceiling out of it, for instance.  Fetching
    at package time ships code no test in this repo has ever seen.

So the upgrade is an ordinary, reviewable commit: run this, run
``theme/sync.py``, run the suite, commit.  ``--check`` is the other half — it
answers "is the pin stale?" without changing anything, and the release workflow
runs it so a pipeline release cannot quietly ship a GramFrame two versions old
(issue #181, where the repo carried v0.1.13 while the target ran v0.1.16).

The release asset is a zip named ``gramframe-<version>.zip`` carrying
``gramframe.bundle.js`` at its root, already under the name both copies use --
there is nothing to rename.  Each copy sits beside a ``VERSION`` file naming
the release it came from; ``tests/test_package_release.py`` enforces that the
two copies stay byte-identical.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = "DeepBlueCLtd/GramFrame"
LATEST_API = "https://api.github.com/repos/{}/releases/latest".format(REPO)
BUNDLE_NAME = "gramframe.bundle.js"

REPO_ROOT = Path(__file__).resolve().parents[2]

# Every place the bundle is vendored. The theme copy travels to the target in
# the release zip and is the one Oxygen deploys; the scripts/vendor copy is
# what publish_html.py's dev preview links -- ``tests/test_package_release.py``
# enforces that those two stay byte-identical. The presentation embed is the
# live demo in the gh-pages deck; no test covers it, which is exactly why it
# belongs here rather than in someone's memory.
COPIES = (
    REPO_ROOT / "theme" / "gramframe-oxygen" / "resources",
    REPO_ROOT / "scripts" / "vendor" / "gramframe",
    REPO_ROOT / "presentation" / "assets" / "embeds",
)


def pinned_version() -> str:
    """The release tag recorded in the first VERSION file, e.g. ``v0.1.18``."""
    version_file = COPIES[0] / "VERSION"
    return version_file.read_text(encoding="utf-8").splitlines()[0].strip()


def _read_url(url: str, accept: str = "") -> bytes:
    """GET a URL, preferring the ``gh`` CLI over a bare HTTPS request.

    ``gh`` is the more reliable of the two in both places this runs: it is
    preinstalled on GitHub's runners, and on a corporate dev host it carries
    the proxy's trust where ``urllib`` hits ``CERTIFICATE_VERIFY_FAILED``.
    Plain ``urllib`` stays as the fallback so the script still works wherever
    ``gh`` is not installed.
    """
    if shutil.which("gh"):
        api_path = url.replace("https://api.github.com/", "", 1)
        command = (["gh", "api", api_path] if api_path != url
                   else ["gh", "api", "--method", "GET", url])
        result = subprocess.run(command, capture_output=True)
        if result.returncode == 0:
            return result.stdout
        # Fall through to urllib rather than failing here: an unauthenticated
        # or rate-limited gh is not a reason to give up on a public asset.
    headers = {"Accept": accept} if accept else {}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def latest_release() -> dict:
    """The newest formal release: ``{"tag": ..., "zip_url": ..., "name": ...}``.

    Draft and pre-releases are excluded by GitHub's ``/releases/latest``
    endpoint itself, which is what makes "formal release" the default here.
    """
    payload = json.loads(
        _read_url(LATEST_API, accept="application/vnd.github+json"))
    assets = [a for a in payload.get("assets", [])
              if a["name"].endswith(".zip")]
    if not assets:
        raise RuntimeError(
            "release {} carries no .zip asset".format(payload.get("tag_name")))
    return {
        "tag": payload["tag_name"],
        "name": assets[0]["name"],
        "zip_url": assets[0]["browser_download_url"],
    }


def fetch_bundle(release: dict) -> bytes:
    """Download the release zip and return the bundle's bytes from inside it."""
    if shutil.which("gh"):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / release["name"]
            result = subprocess.run(
                ["gh", "release", "download", release["tag"], "--repo", REPO,
                 "--pattern", release["name"], "--output", str(target)],
                capture_output=True)
            if result.returncode == 0:
                archive = target.read_bytes()
            else:
                archive = _read_url(release["zip_url"])
    else:
        archive = _read_url(release["zip_url"])
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = [n for n in zf.namelist() if n.rsplit("/", 1)[-1] == BUNDLE_NAME]
        if not names:
            raise RuntimeError(
                "{} holds no {} (found: {})".format(
                    release["name"], BUNDLE_NAME, ", ".join(zf.namelist())))
        return zf.read(names[0])


def write_copies(release: dict, payload: bytes) -> None:
    """Install the bundle and its VERSION note into every vendored copy."""
    note = (
        "{tag}\n"
        "source: https://github.com/{repo}/releases/download/{tag}/{name}\n"
        "asset:  {bundle}\n"
    ).format(tag=release["tag"], repo=REPO, name=release["name"],
             bundle=BUNDLE_NAME)
    for directory in COPIES:
        (directory / BUNDLE_NAME).write_bytes(payload)
        # Path.write_text has no newline kwarg on the 3.9 floor, and these
        # notes are compared across copies, so pin LF explicitly.
        with open(directory / "VERSION", "w", encoding="utf-8", newline="\n") as fh:
            fh.write(note)
        print("  {}  <- {}".format(
            os.path.relpath(directory, REPO_ROOT).replace("\\", "/"),
            release["tag"]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true",
        help="report whether the pin is stale and change nothing; exit 1 when "
             "a newer release exists")
    args = parser.parse_args(argv)

    pinned = pinned_version()
    try:
        release = latest_release()
    except (urllib.error.URLError, OSError, RuntimeError) as exc:
        # Never fail a build because GitHub was unreachable: an offline dev
        # host and a flaky runner are both normal, and neither is evidence
        # that the pin is wrong.
        print("could not reach the GramFrame releases API ({}); "
              "pinned at {}".format(exc, pinned))
        return 0

    if release["tag"] == pinned:
        print("GramFrame is current: {}".format(pinned))
        return 0

    if args.check:
        print("GramFrame is stale: pinned {}, latest {}".format(
            pinned, release["tag"]))
        print("run .github/scripts/update_gramframe.py, then theme/sync.py, "
              "then the test suite")
        return 1

    print("upgrading GramFrame {} -> {}".format(pinned, release["tag"]))
    payload = fetch_bundle(release)
    write_copies(release, payload)
    print("\nnow run:  python theme/sync.py     "
          "# propagate into the template and the committed builds")
    print("then:     python -m unittest discover tests/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

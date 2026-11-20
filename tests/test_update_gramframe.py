"""Tests for .github/scripts/update_gramframe.py's release lookup.

Network is mocked at ``_read_url`` (the API) and ``urllib.request.build_opener``
(the ``/releases/latest/download`` redirect fallback), so this runs offline.
"""
from __future__ import annotations

import contextlib
import email.message
import importlib.util
import io
import json
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "update_gramframe.py"


def _load():
    spec = importlib.util.spec_from_file_location("update_gramframe", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


u = _load()

API_403 = urllib.error.HTTPError(u.LATEST_API, 403, "Forbidden", None, None)


def _redirect_opener(code, location):
    """A build_opener stand-in whose open() raises the given HTTP answer."""
    headers = email.message.Message()
    if location:
        headers["Location"] = location

    class Opener:
        def open(self, request, timeout=None):
            raise urllib.error.HTTPError(request.full_url, code, "x", headers, None)

    return lambda *handlers: Opener()


class LatestReleaseTests(unittest.TestCase):
    def test_api_answer_is_used_when_available(self):
        payload = {"tag_name": "v9.9.9", "assets": [
            {"name": "gramframe-9.9.9.zip", "browser_download_url": "https://x/z.zip"}]}
        with mock.patch.object(u, "_read_url", return_value=json.dumps(payload).encode()), \
             mock.patch("urllib.request.build_opener") as opener:
            release = u.latest_release()
        self.assertEqual(release, {"tag": "v9.9.9", "name": "gramframe-9.9.9.zip",
                                   "zip_url": "https://x/z.zip"})
        opener.assert_not_called()

    def test_refused_api_falls_back_to_download_redirect(self):
        location = ("https://github.com/DeepBlueCLtd/GramFrame/releases/download/"
                    "v0.4.0/gramframe.bundle.js")
        with mock.patch.object(u, "_read_url", side_effect=API_403), \
             mock.patch("urllib.request.build_opener", _redirect_opener(302, location)), \
             contextlib.redirect_stdout(io.StringIO()):
            release = u.latest_release()
        self.assertEqual(release["tag"], "v0.4.0")
        self.assertEqual(release["name"], "gramframe-0.4.0.zip")
        self.assertEqual(
            release["zip_url"],
            "https://github.com/DeepBlueCLtd/GramFrame/releases/download/"
            "v0.4.0/gramframe-0.4.0.zip")

    def test_non_redirect_answer_raises(self):
        with mock.patch.object(u, "_read_url", side_effect=API_403), \
             mock.patch("urllib.request.build_opener", _redirect_opener(403, "")):
            with self.assertRaises(RuntimeError):
                u.latest_release()


class CheckTests(unittest.TestCase):
    def _check(self, release=None, error=None):
        patch = (mock.patch.object(u, "latest_release", side_effect=error) if error
                 else mock.patch.object(u, "latest_release", return_value=release))
        with patch, mock.patch.object(u, "pinned_version", return_value="v0.3.2"), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            code = u.main(["--check"])
        return code, out.getvalue()

    def test_stale_pin_exits_1(self):
        code, _ = self._check(u._release_for_tag("v0.4.0"))
        self.assertEqual(code, 1)

    def test_current_pin_exits_0(self):
        code, out = self._check(u._release_for_tag("v0.3.2"))
        self.assertEqual(code, 0)
        self.assertIn("current", out)

    def test_both_lookups_failing_still_exits_0(self):
        code, out = self._check(error=RuntimeError("API: x; redirect: y"))
        self.assertEqual(code, 0)
        self.assertIn("could not reach", out)


if __name__ == "__main__":
    unittest.main()

"""Static checks of run_pipeline.bat (User Story 6).

Static parsing rather than execution because the suite runs on the
air-gapped network, which may not have ``cmd.exe``. The contract from
contracts/cli-contracts.md is that the wrapper invokes the extractor,
pauses for review, then invokes the generator, with errorlevel checks
between Python stages.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


class RunPipelineBatTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = (REPO_ROOT / "run_pipeline.bat").read_text(encoding="utf-8")

    def test_batch_file_invokes_snapshot_extract_then_generate(self) -> None:
        # Feature 007 inserts a snapshot stage before extract. New order:
        # snapshot -> extract -> pause -> generate.
        snapshot_idx = self.text.find("snapshot_analysis_docs.py")
        extract_idx = self.text.find("extract_to_csv.py")
        pause_idx = self.text.find("pause")
        generate_idx = self.text.find("generate_dita.py")
        self.assertGreater(snapshot_idx, -1)
        self.assertGreater(extract_idx, -1)
        self.assertGreater(pause_idx, -1)
        self.assertGreater(generate_idx, -1)
        self.assertLess(snapshot_idx, extract_idx)
        self.assertLess(extract_idx, pause_idx)
        self.assertLess(pause_idx, generate_idx)
        # errorlevel guard appears after each Python invocation (now 3 stages).
        guards = re.findall(r"if\s+errorlevel\s+1\s+goto\s+error", self.text, re.IGNORECASE)
        self.assertGreaterEqual(len(guards), 3,
                                "must guard snapshot, extract and generate with "
                                "errorlevel checks")

    def test_batch_forwards_input_root_to_snapshot(self) -> None:
        self.assertRegex(self.text, r"--content-root\s+%1")

    def test_batch_forwards_input_root_argument(self) -> None:
        # %1 must reach both --input-root (extractor) and --image-root (generator).
        self.assertRegex(self.text, r"--input-root\s+%1")
        self.assertRegex(self.text, r"--image-root\s+%1")


if __name__ == "__main__":
    unittest.main()

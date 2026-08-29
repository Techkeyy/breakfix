from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from breakfix.web import _load_runs


class WebEvidenceTests(unittest.TestCase):
    def test_final_summary_is_visible_in_run_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "evidence"
            run = root / "final-eval-test"
            run.mkdir(parents=True)
            (run / "final-summary.json").write_text(
                json.dumps({"primary_gate": "PASS"}), encoding="utf-8"
            )
            runs = _load_runs(root)
            self.assertEqual(runs[0]["run_id"], "final-eval-test")
            self.assertEqual(runs[0]["outcome"], "PASS")
            self.assertEqual(runs[0]["purpose"], "Final independent evaluation")


if __name__ == "__main__":
    unittest.main()

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

            demo = root / "canonical-demo-test"
            demo.mkdir(parents=True)
            (demo / "analysis.json").write_text(
                json.dumps({"outcome": "CONFIRMED BREAK"}), encoding="utf-8"
            )
            (demo / "canonical-demo-result.json").write_text(
                json.dumps({"verification": {"status": "VERIFIED"}}), encoding="utf-8"
            )
            runs = _load_runs(root)
            self.assertEqual(runs[0]["run_id"], "final-eval-test")
            self.assertEqual(runs[1]["outcome"], "VERIFIED")
            self.assertEqual(runs[1]["purpose"], "Canonical end-to-end demo")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for offline benchmark evidence history."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/summarize-benchmark-history.py"


class HistoryTests(unittest.TestCase):
    def test_history_output_and_reject_malformed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "sample"
            data.mkdir()
            manifest = {
                "baseline_commit": "a" * 40,
                "candidate_commit": "b" * 40,
                "workload_id": "synthetic",
                "mode": "cross-revision",
                "repetitions_per_side": 3,
            }
            (data / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            metrics = ["realtime_factor", "peak_process_tree_rss_kb", "peak_ffmpeg_rss_kb"]
            rows = [{"metric": metric, "baseline": 100, "candidate": 105,
                     "change_pct": 5, "regression": False} for metric in metrics]
            compare = data / "paired-performance-comparison.json"
            compare.write_text(json.dumps(rows), encoding="utf-8")
            output = root / "output"
            cmd = [sys.executable, str(SCRIPT), str(data), "--output-dir", str(output)]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            result = json.loads((output / "history.json").read_text(encoding="utf-8"))
            self.assertEqual(len(result["records"]), 1)
            self.assertIn("synthetic", (output / "history.md").read_text(encoding="utf-8"))
            csv_text = (output / "trend.csv").read_text(encoding="utf-8")
            self.assertEqual(len(csv_text.strip().splitlines()), 4)
            self.assertIn("realtime_factor", csv_text)
            svg = (output / "trend.svg").read_text(encoding="utf-8")
            self.assertIn("<svg", svg)
            self.assertIn("polyline", svg)
            rows[0]["change_pct"] = 18
            compare.write_text(json.dumps(rows), encoding="utf-8")
            alert_cmd = cmd + ["--alert-threshold-percent", "15"]
            alert_result = subprocess.run(alert_cmd, capture_output=True, text=True)
            self.assertEqual(alert_result.returncode, 1)
            alerts = json.loads((output / "regression-alerts.json").read_text(encoding="utf-8"))
            self.assertEqual(len(alerts["alerts"]), 1)
            self.assertEqual(alerts["alerts"][0]["metric"], "realtime_factor")
            alert_md = (output / "regression-alerts.md").read_text(encoding="utf-8")
            self.assertIn("realtime_factor", alert_md)
            self.assertIn("18.00%", alert_md)
            rows[0]["change_pct"] = "nan"
            compare.write_text(json.dumps(rows), encoding="utf-8")
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Tests for offline benchmark evidence history."""
import json
import hashlib
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
                "environment": {"system": "Linux", "machine": "x86_64",
                                "python": "3.12", "runner_image": "ubuntu24",
                                "runner_arch": "X64", "config_sha256": "a" * 64,
                                "ffmpeg_version": "ffmpeg version 7.0",
                                "go_version": "go version go1.25 linux/amd64",
                                "cpu_model": "Test CPU"},
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
            incompatible = subprocess.run(
                cmd + ["--require-workload-id", "other-workload"],
                capture_output=True, text=True)
            self.assertNotEqual(incompatible.returncode, 0)
            self.assertIn("workload mismatch", incompatible.stderr)
            insufficient = subprocess.run(
                cmd + ["--min-repetitions", "4"], capture_output=True, text=True)
            self.assertNotEqual(insufficient.returncode, 0)
            self.assertIn("insufficient repetitions", insufficient.stderr)
            compatible = subprocess.run(
                cmd + ["--require-workload-id", "synthetic", "--min-repetitions", "3"],
                capture_output=True, text=True)
            self.assertEqual(compatible.returncode, 0)
            matched = subprocess.run(
                cmd + ["--require-matching-environment"],
                capture_output=True, text=True)
            self.assertEqual(matched.returncode, 0)
            manifest["environment"]["config_sha256"] = ""
            (data / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            unmatched = subprocess.run(
                cmd + ["--require-matching-environment"],
                capture_output=True, text=True)
            self.assertNotEqual(unmatched.returncode, 0)
            self.assertIn("provenance", unmatched.stderr)
            manifest["environment"]["config_sha256"] = "a" * 64
            (data / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            manifest["environment"]["ffmpeg_version"] = ""
            (data / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            missing_tool = subprocess.run(
                cmd + ["--require-matching-environment"],
                capture_output=True, text=True)
            self.assertNotEqual(missing_tool.returncode, 0)
            manifest["environment"]["ffmpeg_version"] = "ffmpeg version 7.0"
            (data / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            fp = "b" * 64
            manifest["baseline"] = ["baseline-01.json"]
            manifest["candidate"] = ["candidate-01.json"]
            for name in manifest["baseline"] + manifest["candidate"]:
                (data / name).write_text(json.dumps([{
                    "input_fingerprint": fp, "workload_id": "synthetic"
                }]), encoding="utf-8")
            (data / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            strict_cmd = cmd + ["--require-matching-inputs"]
            self.assertEqual(subprocess.run(strict_cmd, capture_output=True).returncode, 0)
            (data / "candidate-01.json").write_text(json.dumps([{
                "input_fingerprint": "c" * 64, "workload_id": "synthetic"
            }]), encoding="utf-8")
            drift = subprocess.run(strict_cmd, capture_output=True, text=True)
            self.assertNotEqual(drift.returncode, 0)
            self.assertIn("drift", drift.stderr)
            checksums = {}
            for name in manifest["baseline"] + manifest["candidate"]:
                checksums[name] = hashlib.sha256((data / name).read_bytes()).hexdigest()
            (data / "evidence-sha256.json").write_text(
                json.dumps(checksums), encoding="utf-8")
            integrity_cmd = cmd + ["--verify-evidence-sha256"]
            self.assertEqual(subprocess.run(integrity_cmd, capture_output=True).returncode, 0)
            (data / "candidate-01.json").write_text("corrupted", encoding="utf-8")
            corrupt = subprocess.run(integrity_cmd, capture_output=True, text=True)
            self.assertNotEqual(corrupt.returncode, 0)
            self.assertIn("checksum mismatch", corrupt.stderr)
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

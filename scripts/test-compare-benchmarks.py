import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("compare-benchmarks.py")
spec = importlib.util.spec_from_file_location("benchmark_compare", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CompareTests(unittest.TestCase):
    def setUp(self):
        self.baseline = {"realtime_factor": 2.0, "peak_process_tree_rss_kb": 200000,
                         "peak_ffmpeg_rss_kb": 150000, "workload_id": "sample-workload"}
    def test_no_regression(self):
        rows, failed = module.compare(self.baseline, dict(self.baseline), 15)
        self.assertFalse(failed)
        self.assertEqual(rows[0]["change_pct"], 0)
    def test_regression(self):
        candidate = dict(self.baseline)
        candidate["peak_ffmpeg_rss_kb"] = 200000
        rows, failed = module.compare(self.baseline, candidate, 15)
        self.assertTrue(failed)
        self.assertTrue(rows[2]["regression"])
    def test_reject_mismatched_workloads(self):
        with self.assertRaises(ValueError):
            module.compare(self.baseline, {**self.baseline, "workload_id": "other"}, 15)

    def test_reject_unlabeled_workload(self):
        with self.assertRaises(ValueError):
            module.compare({**self.baseline, "workload_id": "unlabeled"}, self.baseline, 15)

    def test_reject_mismatched_input_fingerprints(self):
        base = {**self.baseline, "input_fingerprint": "abc"}
        candidate = {**self.baseline, "input_fingerprint": "def"}
        with self.assertRaises(ValueError):
            module.compare(base, candidate, 15)

    def test_reject_invalid_metric(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            path.write_text(json.dumps([{**self.baseline, "realtime_factor": 0}]))
            with self.assertRaises(ValueError):
                module.read_run(path)
    def test_cli_regression_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp) / "base.json"
            cand = Path(temp) / "candidate.json"
            base.write_text(json.dumps([self.baseline]))
            cand.write_text(json.dumps([{**self.baseline, "realtime_factor": 2.4}]))
            result = subprocess.run([sys.executable, str(SCRIPT), str(base),
                                     str(cand), "--max-regression-percent", "10"],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
    def test_reject_multiple_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            path.write_text(json.dumps([self.baseline, self.baseline]))
            with self.assertRaises(ValueError):
                module.read_run(path)

if __name__ == "__main__":
    unittest.main()

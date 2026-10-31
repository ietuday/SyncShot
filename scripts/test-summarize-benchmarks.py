import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("summarize-benchmarks.py")

class BenchmarkSummaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.run = self.root / "run-example"
        self.run.mkdir()

    def write_measurement(self, exit_code="0", bytes_written="1024", duration="12.5"):
        with (self.run / "measurements.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["start_utc", "elapsed_seconds", "peak_process_tree_rss_kb",
                             "peak_ffmpeg_rss_kb", "exit_code", "output_bytes"])
            writer.writerow(["2026-10-31T00:00:00Z", "25", "200000", "150000", exit_code, bytes_written])
        (self.run / "output-duration.txt").write_text(duration + "\n", encoding="utf-8")

    def execute(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root)],
                              capture_output=True, text=True, check=False)

    def test_success(self):
        self.write_measurement()
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        item = json.loads(result.stdout)[0]
        self.assertEqual(item["realtime_factor"], 2)
        self.assertEqual(item["workload_id"], "unlabeled")
        self.assertEqual(item["peak_ffmpeg_rss_kb"], 150000)

    def test_reject_failed_run(self):
        self.write_measurement(exit_code="1")
        self.assertNotEqual(self.execute().returncode, 0)

    def test_reject_empty_output(self):
        self.write_measurement(bytes_written="0")
        self.assertNotEqual(self.execute().returncode, 0)

    def test_reject_missing_duration(self):
        self.write_measurement()
        (self.run / "output-duration.txt").unlink()
        self.assertNotEqual(self.execute().returncode, 0)

    def test_reject_nonfinite_duration(self):
        self.write_measurement(duration="NaN")
        self.assertNotEqual(self.execute().returncode, 0)

    def test_reject_no_runs(self):
        self.run.rmdir()
        self.assertNotEqual(self.execute().returncode, 0)

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

script=Path(__file__).with_name("summarize-real-media-qualification.py")
spec=importlib.util.spec_from_file_location("qualification_summary",script)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_one_benchmark_is_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)
            run=report/"run-abc"
            run.mkdir()
            (run/"measurements.csv").write_text(
                "start_utc,elapsed_seconds,peak_process_tree_rss_kb,peak_ffmpeg_rss_kb,exit_code,output_bytes\n"
                "2026-11-01T00:00:00Z,42,4096,2048,0,8192\n")
            data=mod.summarize(report)
            self.assertEqual(data["status"],"passed")
            self.assertEqual(data["peak_ffmpeg_rss_mib"],2)
            self.assertTrue((report/"summary.md").exists())
            self.assertEqual(json.loads((report/"summary.json").read_text())["elapsed_seconds"],42)

    def test_multiple_runs_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)
            for name in ["run-a","run-b"]:
                (report/name).mkdir()
                (report/name/"measurements.csv").write_text("x\n1\n")
            with self.assertRaises(ValueError):
                mod.summarize(report)

if __name__=="__main__":
    unittest.main()

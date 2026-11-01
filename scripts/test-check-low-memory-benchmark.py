#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("rss",Path(__file__).with_name("check-low-memory-benchmark.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEADER="start_utc,elapsed_seconds,peak_process_tree_rss_kb,peak_ffmpeg_rss_kb,exit_code,output_bytes\n"
class Tests(unittest.TestCase):
    def test_single_successful_measurement(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/"run-one";report.mkdir()
            (report/"measurements.csv").write_text(HEADER+"now,12,4096,2048,0,100\n")
            mod.validate(Path(tmp),8)
    def test_multiple_measurements_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("run-a","run-b"):
                report=Path(tmp)/name;report.mkdir()
                (report/"measurements.csv").write_text(HEADER+"now,12,4096,2048,0,100\n")
            with self.assertRaisesRegex(ValueError,"exactly one"):
                mod.validate(Path(tmp),8)
    def test_missing_rss_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=Path(tmp)/"run-one";report.mkdir()
            (report/"measurements.csv").write_text(HEADER+"now,12,4096,0,0,100\n")
            with self.assertRaisesRegex(ValueError,"not recorded"):
                mod.validate(Path(tmp),8)
if __name__=="__main__":
    unittest.main()

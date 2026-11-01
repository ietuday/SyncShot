import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("cue_check", Path(__file__).with_name("check-subtitle-cue-timing.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CueTests(unittest.TestCase):
    def check(self, caption, duration="18.0"):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "captions.srt"
            p.write_text(caption, encoding="utf-8")
            with patch.object(module.subprocess, "run", return_value=SimpleNamespace(stdout=duration)):
                return module.inspect(p, Path(tmp) / "video.mp4")

    def test_valid_cues(self):
        data = "1\n00:00:01,000 --> 00:00:05,000\nHello\n\n2\n00:00:08,000 --> 00:00:12,000\nWorld\n"
        result = self.check(data)
        self.assertEqual(result["cue_count"], 2)
        self.assertEqual(result["cues"][0]["midpoint_seconds"], 3)

    def test_cue_beyond_video(self):
        with self.assertRaises(ValueError):
            self.check("1\n00:00:17,000 --> 00:00:21,000\nToo late\n")

    def test_overlapping_cues(self):
        with self.assertRaises(ValueError):
            self.check("1\n00:00:01,000 --> 00:00:05,000\nA\n\n2\n00:00:04,000 --> 00:00:09,000\nB\n")

if __name__ == "__main__":
    unittest.main()

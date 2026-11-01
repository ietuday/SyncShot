import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("visual", Path(__file__).with_name("check-shorts-visual-content.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class VisualTests(unittest.TestCase):
    def test_bright_detailed_frame(self):
        pixels = bytes([40, 200] * 2048)
        with patch.object(module.subprocess, "run", return_value=SimpleNamespace(stdout=pixels)):
            data = module.sample_frame("clip.mp4", 2)
        self.assertGreater(data["mean_luma"], 12)
        self.assertGreater(data["luma_stddev"], 5)

    def test_truncated_frame_is_rejected(self):
        with patch.object(module.subprocess, "run", return_value=SimpleNamespace(stdout=b"tiny")):
            with self.assertRaises(ValueError):
                module.sample_frame("clip.mp4", 2)

    def test_blank_samples_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "clip.mp4").write_bytes(b"fixture")
            probe = SimpleNamespace(stdout="8.0")
            frame = {"timestamp_seconds": 4, "mean_luma": 0, "luma_stddev": 0}
            with patch.object(module.subprocess, "run", return_value=probe):
                with patch.object(module, "sample_frame", return_value=frame):
                    with self.assertRaises(ValueError):
                        module.inspect(tmp)

    def test_valid_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "clip.mp4").write_bytes(b"fixture")
            probe = SimpleNamespace(stdout="8.0")
            frame = {"timestamp_seconds": 4, "mean_luma": 120, "luma_stddev": 30}
            with patch.object(module.subprocess, "run", return_value=probe):
                with patch.object(module, "sample_frame", return_value=frame):
                    result = module.inspect(tmp)
            self.assertEqual(result["clip_count"], 1)
            self.assertEqual(len(result["clips"][0]["samples"]), 3)

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("summarize-render-failure.py")
spec = importlib.util.spec_from_file_location("render_failure", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RenderFailureTests(unittest.TestCase):
    def test_sigkill_is_not_proof_of_oom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.log").write_text("ffmpeg exited: signal: killed")
            result = module.summarize(root, 137)
            self.assertTrue(result["ffmpeg_sigkill_reported"])
            self.assertFalse(result["kernel_oom_confirmed"])
            self.assertTrue((root / "failure-diagnostics.json").exists())

    def test_normal_failure_has_general_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run.log").write_text("ffmpeg exited: exit status 1")
            result = module.summarize(root, 1)
            self.assertFalse(result["possible_memory_pressure"])
            self.assertTrue(result["suggestions"])

if __name__ == "__main__":
    unittest.main()

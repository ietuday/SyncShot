#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("analysis",Path(__file__).with_name("analyze-qualification-failure.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_sigkill_is_not_called_confirmed_oom(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            run=root/"run-abc"
            run.mkdir()
            (run/"run.log").write_text("ffmpeg: signal: killed")
            result=mod.analyze(root,"benchmark",137)
            self.assertEqual(result["category"],"ffmpeg_sigkill")
            self.assertNotIn("confirmed",result["category"])
            self.assertTrue((root/"failure-analysis.json").exists())
    def test_memory_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=mod.analyze(Path(tmp),"memory",1)
            self.assertEqual(result["category"],"memory_budget_exceeded")

if __name__=="__main__":
    unittest.main()

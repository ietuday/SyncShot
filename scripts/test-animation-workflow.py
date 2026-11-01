#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location("orchestrator",Path(__file__).with_name("animation-workflow.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_preview_never_executes_paid_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            args=SimpleNamespace(stage="preview-images",workdir=Path(temp),scene_seconds=8,limit=3,
                                 image_urls=None,tasks=None,clips_dir=None,output=None)
            calls=[]
            mod.run(args,runner=lambda command,**kwargs:calls.append(command))
            self.assertEqual(len(calls),1)
            self.assertNotIn("--execute",calls[0])
            self.assertNotIn("--download",calls[0])
    def test_requires_external_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            args=SimpleNamespace(stage="assemble",workdir=Path(temp),scene_seconds=8,limit=3,
                                 image_urls=None,tasks=None,clips_dir=None,output=None)
            with self.assertRaisesRegex(ValueError,"clips-dir"):
                mod.run(args)
    def test_stage_values(self):
        self.assertEqual(len(mod.STAGES),6)

if __name__=="__main__":
    unittest.main()

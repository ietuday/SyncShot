#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("check",Path(__file__).with_name("check-animation-clips.py"))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
PLAN={"version":1,"scenes":[{"index":1},{"index":2}]}
VALID={"format":{"duration":"5.00"},"streams":[{"codec_type":"video"}]}

class Tests(unittest.TestCase):
    def test_missing_and_valid(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/"scene-0001.mp4").write_bytes(b"fixture")
            result=mod.check(PLAN,base,lambda _:VALID)
            self.assertFalse(result["complete"])
            self.assertEqual(result["counts"],{"ready":1,"missing":1,"invalid":0})
    def test_broken_video(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/"scene-0001.mp4").write_bytes(b"bad")
            result=mod.check({"version":1,"scenes":[{"index":1}]},base,
                lambda _:{"format":{"duration":"NaN"},"streams":[]})
            self.assertEqual(result["counts"]["invalid"],1)
    def test_complete(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            for i in (1,2):(base/f"scene-{i:04d}.mp4").write_bytes(b"fixture")
            self.assertTrue(mod.check(PLAN,base,lambda _:VALID)["complete"])
    def test_wrong_index(self):
        with self.assertRaisesRegex(ValueError,"index"):
            mod.check({"version":1,"scenes":[{"index":99}]},Path("/tmp"),lambda _:VALID)
if __name__=="__main__":unittest.main()

#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("clipverify",Path(__file__).with_name("verify-provider-clip.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PLAN={"version":1,"scenes":[{"index":1,"start":0,"end":5}]}
def provider(seconds):
    return {"streams":[{"codec_type":"video"}],"format":{"duration":str(seconds)}}
class Tests(unittest.TestCase):
    def test_matching_clip(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"clip.mp4";path.write_bytes(b"fixture")
            result=m.verify(PLAN,path,lambda _:provider(5))
            self.assertTrue(result["ready"])
            self.assertFalse(result["will_loop"])
    def test_duration_adaptation(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"clip.mp4";path.write_bytes(b"fixture")
            self.assertTrue(m.verify(PLAN,path,lambda _:provider(3))["will_loop"])
            self.assertTrue(m.verify(PLAN,path,lambda _:provider(7))["will_trim"])
    def test_reject_missing_or_audio_only(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"clip.mp4"
            with self.assertRaisesRegex(ValueError,"missing"):
                m.verify(PLAN,path,lambda _:provider(5))
            path.write_bytes(b"fixture")
            with self.assertRaisesRegex(ValueError,"video"):
                m.verify(PLAN,path,lambda _:{"streams":[{"codec_type":"audio"}],"format":{"duration":"5"}})
if __name__=="__main__":unittest.main()

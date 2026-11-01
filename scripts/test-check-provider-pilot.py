#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("readiness",Path(__file__).with_name("check-provider-pilot.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_readiness_and_bad_duration(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"audio.m4a";file.write_bytes(b"fixture")
            plan={"duration_seconds":5,"audio":str(file),"scenes":[
                {"index":1,"start":0,"end":5,"visual_prompt":"Sage walking"}]}
            urls={"1":"https://example.com/pilot.png"}
            self.assertTrue(m.inspect(plan,urls)["ready"])
            plan["duration_seconds"]=30
            self.assertFalse(m.inspect(plan,urls)["ready"])
    def test_no_local_url(self):
        out=m.inspect({"scenes":[],"audio":"/missing"}, {"1":"file:///tmp/image.png"})
        self.assertFalse(out["ready"])
        self.assertEqual(out["provider_requests_submitted"],0)
if __name__=="__main__":unittest.main()

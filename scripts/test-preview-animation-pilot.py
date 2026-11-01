#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("preview",Path(__file__).with_name("preview-animation-pilot.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_preview_has_no_paid_flags(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pilot.json"
            p.write_text(json.dumps({"version":1,"pilot_audio_prepared":True,"scenes":[{"index":1}]}))
            commands=m.commands(p,Path(d)/"urls.json",1,Path(d),Path(d))
            self.assertEqual(len(commands),2)
            self.assertTrue(all("--execute" not in c and "--download" not in c for c in commands))
    def test_requires_prepared_pilot(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"pilot.json"
            p.write_text(json.dumps({"version":1,"scenes":[{"index":1}]}))
            with self.assertRaisesRegex(ValueError,"pilot-ready"):
                m.commands(p,None,1,Path(d),Path(d))
if __name__=="__main__":unittest.main()

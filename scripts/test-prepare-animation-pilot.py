#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("pilot",Path(__file__).with_name("prepare-animation-pilot.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PLAN={"version":1,"audio":"example.m4a","duration_seconds":925,
      "scenes":[{"index":n+1,"start":n*8,"end":(n+1)*8,
                 "visual_prompt":f"Animated scene {n+1}"} for n in range(10)]}

class Tests(unittest.TestCase):
    def test_bounded_default(self):
        output=module.prepare(PLAN)
        self.assertEqual(len(output["scenes"]),4)
        self.assertEqual(output["duration_seconds"],30)
        self.assertEqual(output["scenes"][-1]["end"],30)
        self.assertTrue(output["pilot"]["audio_requires_trim"])
    def test_max_scenes(self):
        result=module.prepare(PLAN,30,2)
        self.assertEqual(result["duration_seconds"],16)
    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            module.prepare(PLAN,0)
        broken={**PLAN,"scenes":[{**PLAN["scenes"][0],"start":2}]}
        with self.assertRaisesRegex(ValueError,"contiguous"):
            module.prepare(broken)
if __name__=="__main__":unittest.main()

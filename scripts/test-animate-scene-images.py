#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location("animate",Path(__file__).with_name("animate-scene-images.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
PLAN={"version":1,"scenes":[{"index":1,"start":0,"end":8,"visual_prompt":"Lord Ram walking peacefully in a forest"}]}
URLS={"1":"https://example.com/scene.png"}

class Tests(unittest.TestCase):
    def test_preview(self):
        jobs=mod.build_jobs(PLAN,URLS,1)
        self.assertEqual(jobs[0]["duration"],5)
        self.assertEqual(jobs[0]["scene"],1)
    def test_requires_url(self):
        with self.assertRaisesRegex(ValueError,"missing"):
            mod.build_jobs(PLAN,{},1)
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            mod.build_jobs(PLAN,{"1":"file:///tmp/scene.png"},1)
    def test_no_task_before_submit(self):
        class Client:
            def __init__(self):self.calls=[]
            class image_to_video:
                @staticmethod
                def create(**kwargs): return SimpleNamespace(id="task-123")
        self.assertEqual(mod.submit(mod.build_jobs(PLAN,URLS,1),Client())[0]["task_id"],"task-123")

if __name__=="__main__":
    unittest.main()

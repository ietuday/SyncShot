#!/usr/bin/env python3
import importlib.util
import unittest
import tempfile
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

    def test_paid_execution_requires_confirmation(self):
        import json
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            plan=root/"plan.json"
            plan.write_text(json.dumps({"version":1,"scenes":[{"index":1,"start":0,"end":5,"visual_prompt":"Forest"},{"index":2,"start":5,"end":10,"visual_prompt":"Sage"}]}))
            urls=root/"urls.json"
            urls.write_text(json.dumps({"1":"https://example.com/image.png","2":"https://example.com/image2.png"}))
            args=["animate-scene-images.py","--plan",str(plan),"--image-urls",str(urls),
                  "--output",str(root/"tasks.json"),"--execute"]
            with patch("sys.argv",args), patch.dict("os.environ",{"RUNWAYML_API_SECRET":"fake"}):
                with self.assertRaises(SystemExit):
                    mod.main()
            self.assertFalse((root/"tasks.json").exists())
            with patch("sys.argv",args+["--limit","2","--confirm-paid-pilot"]), patch.dict("os.environ",{"RUNWAYML_API_SECRET":"fake"}):
                with self.assertRaises(SystemExit):
                    mod.main()
            self.assertFalse((root/"tasks.json").exists())

if __name__=="__main__":
    unittest.main()

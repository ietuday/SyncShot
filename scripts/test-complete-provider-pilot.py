#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("complete",Path(__file__).with_name("complete-provider-pilot.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TASKS={"mode":"submitted","clips":[{"scene":1,"task_id":"task-1"}]}
PLAN={"version":1,"scenes":[{"index":1,"start":0,"end":5}]}
class Tests(unittest.TestCase):
    def test_requires_opt_in_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); clips=root/"clips";clips.mkdir()
            called=[]
            def collect(*args):
                called.append(args[3])
                return {"clips":[{"scene":1,"status":"SUCCEEDED"}]}
            with self.assertRaisesRegex(ValueError,"--download"):
                m.finish(TASKS,PLAN,None,clips,root/"demo.mp4",root/"report.json",
                         collector=collect,builder=lambda *args:self.fail("must not assemble"))
            self.assertEqual(called,[False])
    def test_download_then_assemble(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); clips=root/"clips";clips.mkdir()
            def collect(*args):
                self.assertTrue(args[3])
                (clips/"scene-0001.mp4").write_bytes(b"fixture")
                return {"clips":[{"scene":1,"status":"SUCCEEDED"}]}
            outcome=m.finish(TASKS,PLAN,None,clips,root/"demo.mp4",root/"report.json",
                   download=True,collector=collect,
                   builder=lambda *args:{"video_output":str(root/"demo.mp4")})
            self.assertTrue(outcome["video_output"].endswith(".mp4"))
    def test_no_multiple_tasks_or_failed_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);clips=root/"clips";clips.mkdir()
            with self.assertRaisesRegex(ValueError,"exactly one"):
                m.finish({"mode":"submitted","clips":TASKS["clips"]*2},
                         PLAN,None,clips,root/"demo.mp4",root/"report.json")
            with self.assertRaisesRegex(ValueError,"not succeeded"):
                m.finish(TASKS,PLAN,None,clips,root/"demo.mp4",root/"report.json",
                         collector=lambda *a:{"clips":[{"status":"FAILED"}]})

    def test_retry_reuses_existing_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);clips=root/"clips";clips.mkdir()
            (clips/"scene-0001.mp4").write_bytes(b"previous download")
            flags=[]
            def collect(*args):
                flags.append(args[3])
                return {"clips":[{"scene":1,"status":"SUCCEEDED"}]}
            result=m.finish(TASKS,PLAN,None,clips,root/"demo.mp4",root/"report.json",
                            download=True,collector=collect,
                            builder=lambda *args:{"video_output":str(root/"demo.mp4")})
            self.assertEqual(flags,[False])
            self.assertEqual(result["video_output"],str(root/"demo.mp4"))
            self.assertEqual((clips/"scene-0001.mp4").read_bytes(),b"previous download")

if __name__=="__main__":unittest.main()

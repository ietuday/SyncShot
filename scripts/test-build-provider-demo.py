#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location("demo", Path(__file__).with_name("build-provider-demo.py"))
m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def test_verify_before_render_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); clips=root/"clips";clips.mkdir()
            (clips/"scene-0001.mp4").write_bytes(b"fixture")
            (root/"audio.m4a").write_bytes(b"fixture")
            plan={"version":1,"audio":str(root/"audio.m4a"),"duration_seconds":5,
                  "scenes":[{"index":1,"start":0,"end":5}]}
            calls=[]
            def verifier(*args):
                calls.append("verify")
                return {"ready":True}
            def assembler(*args):
                calls.append("assemble")
                (root/"demo.mp4").write_bytes(b"demo")
            report=root/"report.json"
            result=m.build_demo(plan, clips, root/"demo.mp4",report,
                                verifier=verifier,probe=lambda _: {},assembler=assembler)
            self.assertEqual(calls,["verify","assemble"])
            self.assertEqual(json.loads(report.read_text())["video_output"],str(root/"demo.mp4"))
            with self.assertRaises(FileExistsError):
                m.build_demo(plan, clips,root/"demo.mp4",root/"new.json",verifier=verifier,assembler=assembler)
    def test_missing_audio_prevents_render(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);clips=root/"clips";clips.mkdir()
            plan={"audio":str(root/"missing.m4a")}
            with self.assertRaisesRegex(ValueError,"narration"):
                m.build_demo(plan,clips,root/"out.mp4",root/"report.json",verifier=lambda *a:{"ready":True},
                             probe=lambda _: {},assembler=lambda *a:self.fail("must not render"))

    def test_assembly_failure_leaves_no_report(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);clips=root/"clips";clips.mkdir()
            (root/"audio.m4a").write_bytes(b"fixture")
            plan={"audio":str(root/"audio.m4a")}
            def fail(*args):
                raise RuntimeError("render failed")
            with self.assertRaisesRegex(RuntimeError,"render failed"):
                m.build_demo(plan,clips,root/"demo.mp4",root/"report.json",
                             verifier=lambda *a:{"ready":True},probe=lambda *a:{},assembler=fail)
            self.assertFalse((root/"report.json").exists())

if __name__=="__main__": unittest.main()

#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("providerpilot",Path(__file__).with_name("prepare-provider-pilot.py"))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
PLAN={"version":1,"pilot_audio_prepared":True,"audio":"pilot.m4a","scenes":[{"index":1,"start":0,"end":5,"visual_prompt":"Animate a forest"}]}
class Tests(unittest.TestCase):
    def test_single_scene(self):
        result=m.build(PLAN,"https://example.com/forest.png")
        self.assertEqual(len(result["plan"]["scenes"]),1)
        self.assertEqual(result["plan"]["duration_seconds"],5)
    def test_no_local_url(self):
        with self.assertRaisesRegex(ValueError,"HTTPS"):
            m.build(PLAN,"file:///home/u/forest.png")
    def test_unprepared_rejected(self):
        with self.assertRaisesRegex(ValueError,"pilot-ready"):
            m.build({**PLAN,"pilot_audio_prepared":False},"https://example.com/image.png")


    def test_real_ffmpeg_single_scene_audio(self):
        import json
        import shutil
        import subprocess
        import tempfile
        from unittest.mock import patch
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("ffmpeg unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=root/"pilot.m4a"
            subprocess.run(["ffmpeg","-v","error","-f","lavfi","-i",
                            "sine=frequency=440:duration=8","-c:a","aac",
                            str(original)],check=True)
            plan={**PLAN,"audio":str(original)}
            planpath=root/"ready.json"
            planpath.write_text(json.dumps(plan))
            with patch("sys.argv",["prepare-provider-pilot","--pilot",str(planpath),
                 "--image-url","https://example.com/image.png",
                 "--plan-output",str(root/"scene.json"),
                 "--urls-output",str(root/"urls.json"),
                 "--audio-output",str(root/"scene.m4a")]):
                m.main()
            result=json.loads((root/"scene.json").read_text())
            self.assertEqual(result["duration_seconds"],5)
            self.assertEqual(result["audio"],str(root/"scene.m4a"))
            self.assertTrue((root/"scene.m4a").is_file())

if __name__=="__main__": unittest.main()

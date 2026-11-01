#!/usr/bin/env python3
"""Integration smoke: real FFmpeg trims pilot audio, preserves original, aligns plan."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(name,alias):
    spec=importlib.util.spec_from_file_location(alias,ROOT/name)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
pilot=load("prepare-animation-pilot.py","pilot")
audio=load("prepare-pilot-audio.py","pilot_audio")

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"ffmpeg/ffprobe required")
class TestPilotIntegration(unittest.TestCase):
    def test_pilot_audio_timing_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            source=root/"original.m4a"
            subprocess.run(["ffmpeg","-v","error","-y","-f","lavfi","-i",
                            "sine=frequency=450:duration=7","-c:a","aac",str(source)],check=True)
            plan={"version":1,"audio":str(source),"duration_seconds":7,
                  "scenes":[{"index":1,"start":0,"end":3,"visual_prompt":"Forest"},
                            {"index":2,"start":3,"end":7,"visual_prompt":"Sage"}]}
            limited=pilot.prepare(plan,limit_seconds=5,max_scenes=2)
            output=root/"pilot.m4a";manifest=root/"ready.json"
            ready=audio.prepare(limited,output,manifest)
            self.assertEqual(ready["duration_seconds"],5)
            self.assertEqual(ready["scenes"][-1]["end"],5)
            self.assertLess(abs(audio.duration_of(output)-5),0.15)
            self.assertGreater(audio.duration_of(source),6)
            self.assertEqual(json.loads(manifest.read_text())["audio"],str(output))
            with self.assertRaises(FileExistsError):
                audio.prepare(limited,output,manifest)

if __name__=="__main__":unittest.main()

#!/usr/bin/env python3
"""Run the verified-provider demo with actual FFmpeg-generated fixture media."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("demo",root/"build-provider-demo.py")
demo=importlib.util.module_from_spec(spec);spec.loader.exec_module(demo)

def run(*command):
    return subprocess.run(command,capture_output=True,text=True,check=True,timeout=90)

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"requires ffmpeg and ffprobe")
class ProviderDemoFFmpegIntegration(unittest.TestCase):
    def test_loop_short_video_and_assemble_narration(self):
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            clips=directory/"clips";clips.mkdir()
            run("ffmpeg","-v","error","-nostdin","-y","-f","lavfi","-i",
                "color=c=red:s=320x180:r=12:d=1","-c:v","libx264","-threads","1",
                "-pix_fmt","yuv420p",str(clips/"scene-0001.mp4"))
            audio=directory/"narration.m4a"
            run("ffmpeg","-v","error","-nostdin","-y","-f","lavfi","-i",
                "sine=frequency=440:duration=3","-c:a","aac",str(audio))
            plan={"version":1,"audio":str(audio),"duration_seconds":3,
                  "scenes":[{"index":1,"start":0,"end":3,"visual_prompt":"Forest movement"}]}
            output=directory/"demo.mp4";report=directory/"report.json"
            details=demo.build_demo(plan,clips,output,report)
            self.assertTrue(details["will_loop"])
            self.assertEqual(json.loads(report.read_text())["video_output"],str(output))
            probe=json.loads(run("ffprobe","-v","error","-show_entries",
                "format=duration:stream=codec_type","-of","json",str(output)).stdout)
            self.assertEqual({s["codec_type"] for s in probe["streams"]},{"audio","video"})
            self.assertLess(abs(float(probe["format"]["duration"])-3),0.4)
            with self.assertRaises(FileExistsError):
                demo.build_demo(plan,clips,output,report)

if __name__=="__main__": unittest.main()

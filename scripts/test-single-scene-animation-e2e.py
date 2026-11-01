#!/usr/bin/env python3
"""Real FFmpeg single-scene integration without network or paid provider calls."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
def load(filename,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/filename)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj)
    return obj

provider=load("prepare-provider-pilot.py","provider_pilot")
animate=load("animate-scene-images.py","animate_pilot")
clips=load("check-animation-clips.py","clip_readiness")
assemble=load("assemble-animated-video.py","assembly_pilot")

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"requires ffmpeg and ffprobe")
class SingleSceneIntegration(unittest.TestCase):
    def test_complete_local_assembly(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            narration=root/"pilot.m4a"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                "-f","lavfi","-i","sine=frequency=440:sample_rate=44100:duration=7",
                "-c:a","aac",str(narration)],check=True)
            pilot={"version":1,"pilot_audio_prepared":True,"audio":str(narration),
                   "style":"mythological_3d","scenes":[
                       {"index":1,"start":0,"end":5,"visual_prompt":"Forest canopy gently sways"},
                       {"index":2,"start":5,"end":7,"visual_prompt":"Sage enters"}]}
            source=root/"pilot-ready.json";source.write_text(json.dumps(pilot))
            plan=root/"scene-plan.json";urls=root/"urls.json";scene_audio=root/"scene.m4a"
            with patch("sys.argv",["prepare-provider-pilot","--pilot",str(source),
                  "--image-url","https://example.com/approved-scene.png",
                  "--plan-output",str(plan),"--urls-output",str(urls),
                  "--audio-output",str(scene_audio)]):
                provider.main()
            data=json.loads(plan.read_text())
            self.assertEqual(data["duration_seconds"],5)
            self.assertEqual(data["audio"],str(scene_audio))
            jobs=animate.build_jobs(data,json.loads(urls.read_text()),1)
            self.assertEqual(len(jobs),1)
            self.assertEqual(jobs[0]["duration"],5)
            directory=root/"clips";directory.mkdir()
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                "-f","lavfi","-i","color=c=blue:s=320x180:r=12:d=1",
                "-c:v","libx264","-threads","1","-pix_fmt","yuv420p",
                str(directory/"scene-0001.mp4")],check=True)
            ready=clips.check(data,directory,clips.ffprobe)
            self.assertTrue(ready["complete"],ready)
            output=root/"animated.mp4"
            assemble.assemble(data,directory,output)
            cp=subprocess.run(["ffprobe","-v","error","-show_entries",
                "format=duration:stream=codec_type,duration","-of","json",str(output)],
                capture_output=True,text=True,check=True)
            media=json.loads(cp.stdout)
            types={s["codec_type"] for s in media["streams"]}
            self.assertEqual(types,{"audio","video"})
            self.assertLess(abs(float(media["format"]["duration"])-5),0.4)
            self.assertTrue(output.stat().st_size>0)
            with self.assertRaises(FileExistsError):
                assemble.assemble(data,directory,output)

if __name__=="__main__":
    unittest.main()

#!/usr/bin/env python3
"""Real FFmpeg integration smoke for Phase 9 assembly, using synthetic media."""
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def import_script(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

assemble = import_script("assemble-animated-video.py", "assembly")
readiness = import_script("check-animation-clips.py", "readiness")

def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=90)

def media(path):
    return json.loads(run("ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,duration",
                          "-of", "json", str(path)).stdout)

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "requires ffmpeg and ffprobe")
class AnimationAssemblyIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.clips = self.root / "clips"
        self.clips.mkdir()
        for n, color in ((1, "blue"), (2, "green")):
            run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c={color}:s=320x180:r=12:d=1",
                "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p",
                str(self.clips / f"scene-{n:04d}.mp4"))
        self.audio = self.root / "narration.m4a"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=450:sample_rate=44100:duration=4",
            "-c:a", "aac", str(self.audio))
        self.plan = {"version": 1, "audio": str(self.audio), "duration_seconds": 4,
                     "scenes": [{"index": 1, "start": 0, "end": 2},
                                {"index": 2, "start": 2, "end": 4}]}

    def test_real_clip_validation_and_render(self):
        check = readiness.check(self.plan, self.clips, readiness.ffprobe)
        self.assertTrue(check["complete"], check)
        output = self.root / "story.mp4"
        assemble.assemble(self.plan, self.clips, output)
        streams = media(output)
        types = {s["codec_type"] for s in streams["streams"]}
        self.assertIn("video", types)
        self.assertIn("audio", types)
        self.assertLess(abs(float(streams["format"]["duration"]) - 4), 0.35)
        video = next(s for s in streams["streams"] if s["codec_type"] == "video")
        audio = next(s for s in streams["streams"] if s["codec_type"] == "audio")
        self.assertLess(abs(float(video["duration"]) - float(audio["duration"])), 0.5)
        with self.assertRaises(FileExistsError):
            assemble.assemble(self.plan, self.clips, output)

    def test_missing_scene_blocks_publication(self):
        (self.clips / "scene-0002.mp4").unlink()
        report = readiness.check(self.plan, self.clips, readiness.ffprobe)
        self.assertEqual(report["counts"]["missing"], 1)
        output = self.root / "story.mp4"
        with self.assertRaisesRegex(ValueError, "missing"):
            assemble.assemble(self.plan, self.clips, output)
        self.assertFalse(output.exists())

    def test_corrupt_scene_not_ready(self):
        (self.clips / "scene-0002.mp4").write_bytes(b"not an mp4")
        report = readiness.check(self.plan, self.clips, readiness.ffprobe)
        self.assertEqual(report["counts"]["invalid"], 1)

if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("transcriber", Path(__file__).with_name("transcribe-audio.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Tests(unittest.TestCase):
    def test_hindi_transcript_storyplan_shape(self):
        parts = [SimpleNamespace(start=0, end=3, text=" जय श्री राम "),
                 SimpleNamespace(start=3, end=5, text="वन में")]
        data = module.build_transcript(Path("inputs/audio/story.m4a"), 5, parts)
        self.assertEqual(data["segments"][0]["text"], "जय श्री राम")
        self.assertEqual(data["duration_seconds"], 5)
        self.assertEqual(len(data["segments"]), 2)

    def test_empty_and_invalid_segments(self):
        with self.assertRaisesRegex(ValueError, "no speech"):
            module.build_transcript(Path("x"), 5, [])
        with self.assertRaisesRegex(ValueError, "timestamps"):
            module.build_transcript(Path("x"), 5, [SimpleNamespace(start=4, end=6, text="bad")])
        with self.assertRaisesRegex(ValueError, "timestamps"):
            module.build_transcript(Path("x"), 5, [
                SimpleNamespace(start=0, end=4, text="one"),
                SimpleNamespace(start=3, end=5, text="overlap")])

    def test_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "transcript.json"
            dest.write_text("original")
            with self.assertRaises(FileExistsError):
                module.save_new(dest, {"segments": []})
            self.assertEqual(dest.read_text(), "original")

    def test_unicode_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "transcript.json"
            module.save_new(dest, {"segments": [{"text": "रामायण"}]})
            self.assertEqual(json.loads(dest.read_text())["segments"][0]["text"], "रामायण")


if __name__ == "__main__":
    unittest.main()

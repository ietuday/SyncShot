#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("scene_images", Path(__file__).with_name("generate-scene-images.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

PNG = b"\x89PNG\r\n\x1a\n" + b"test-fixture"


class SceneImageTests(unittest.TestCase):
    def plan(self, directory):
        path = Path(directory) / "plan.json"
        path.write_text(json.dumps({"version": 1, "scenes": [
            {"index": 1, "start": 0, "end": 5, "visual_prompt": "Forest with sage"},
            {"index": 2, "start": 5, "end": 10, "visual_prompt": "Shri Ram walking"}]}))
        return path

    def test_preview_never_creates_files(self):
        with tempfile.TemporaryDirectory() as directory:
            scenes = module.load_plan(self.plan(directory), 2)
            output = Path(directory) / "images"
            results = module.generate(scenes, output, False)
            self.assertEqual(len(results), 2)
            self.assertFalse(output.exists())

    def test_explicit_execute_calls_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            scenes = module.load_plan(self.plan(directory), 1)
            target = Path(directory) / "images"
            calls = []
            def stub(prompt, key):
                calls.append((prompt, key))
                return PNG
            module.generate(scenes, target, True, "test-key", provider=stub)
            self.assertEqual(len(calls), 1)
            self.assertEqual((target / "scene-0001.png").read_bytes(), PNG)
            with self.assertRaises(FileExistsError):
                module.generate(scenes, target, True, "test-key", provider=stub)

    def test_requires_key_and_rejects_bad_image(self):
        with tempfile.TemporaryDirectory() as directory:
            scenes = module.load_plan(self.plan(directory), 1)
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                module.generate(scenes, Path(directory) / "images", True)
            with self.assertRaisesRegex(ValueError, "invalid PNG"):
                module.generate(scenes, Path(directory) / "images", True,
                                "test-key", provider=lambda *_: b"not a png")

    def test_invalid_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.plan(directory)
            with self.assertRaisesRegex(ValueError, "limit"):
                module.load_plan(path, 0)
            value = json.loads(path.read_text())
            value["scenes"][0]["visual_prompt"] = ""
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "prompt"):
                module.load_plan(path, 2)


if __name__ == "__main__":
    unittest.main()

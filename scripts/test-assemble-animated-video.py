#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("assembly", Path(__file__).with_name("assemble-animated-video.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Tests(unittest.TestCase):
    def setup_data(self, root):
        clips = root / "clips"
        clips.mkdir()
        (clips / "scene-0001.mp4").write_bytes(b"test")
        (clips / "scene-0002.mp4").write_bytes(b"test")
        (root / "audio.m4a").write_bytes(b"audio")
        plan = {"version": 1, "duration_seconds": 10, "audio": str(root / "audio.m4a"),
                "scenes": [{"index": 1, "start": 0, "end": 4},
                           {"index": 2, "start": 4, "end": 10}]}
        return clips, plan

    def test_contiguous_scenes_and_loop_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clips, plan = self.setup_data(root)
            segments, duration = mod.validate_plan(plan, clips)
            self.assertEqual(duration, 10)
            commands, _, final = mod.build_commands(segments, root / "audio.m4a", root, root / "out.mp4")
            self.assertEqual(len(commands), 2)
            self.assertIn("-stream_loop", commands[0][0])
            self.assertIn("-map", final)

    def test_rejects_gaps(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clips, plan = self.setup_data(root)
            plan["scenes"][1]["start"] = 5
            with self.assertRaisesRegex(ValueError, "gaps"):
                mod.validate_plan(plan, clips)

    def test_rejects_missing_clip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clips, plan = self.setup_data(root)
            (clips / "scene-0002.mp4").unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                mod.validate_plan(plan, clips)

    def test_does_not_overwrite_final_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clips, plan = self.setup_data(root)
            out = root / "out.mp4"
            out.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                mod.assemble(plan, clips, out)
            self.assertEqual(out.read_bytes(), b"original")

    def test_mocked_render_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            clips, plan = self.setup_data(root)
            commands = []
            def fake_run(command, check):
                commands.append(command)
                Path(command[-1]).write_bytes(b"rendered")
            out = root / "out.mp4"
            mod.assemble(plan, clips, out, runner=fake_run)
            self.assertEqual(len(commands), 3)
            self.assertEqual(out.read_bytes(), b"rendered")


if __name__ == "__main__":
    unittest.main()

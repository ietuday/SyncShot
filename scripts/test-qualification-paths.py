import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("paths", Path(__file__).with_name("check-qualification-paths.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class QualificationPathTests(unittest.TestCase):
    def test_output_outside_inputs_and_reports_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            media=root/"media"
            media.mkdir()
            config=root/"config.json"
            config.write_text("{}")
            output=root/"videos"/"new.mp4"
            self.assertEqual(mod.guard(output, config, root/"reports", [media]), str(output.resolve()))

    def test_rejects_output_in_media_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            media=root/"media"
            media.mkdir()
            config=root/"config.json"
            config.write_text("{}")
            with self.assertRaises(ValueError):
                mod.guard(media/"video.mp4", config, root/"reports", [media])

    def test_rejects_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config=root/"config.json"
            config.write_text("{}")
            output=root/"clip.mp4"
            output.write_bytes(b"original")
            with self.assertRaises(ValueError):
                mod.guard(output, config, root/"reports", [config])

    def test_rejects_output_in_evidence_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config=root/"config.json"
            config.write_text("{}")
            reports=root/"reports"
            with self.assertRaises(ValueError):
                mod.guard(reports/"clip.mp4", config, reports, [config])

    def test_rejects_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config=root/"config.json"
            config.write_text("{}")
            with self.assertRaises(ValueError):
                mod.guard(root/"out.mp4",config,root/"reports",[root/"missing"])

if __name__=="__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime

spec = importlib.util.spec_from_file_location("status", Path(__file__).with_name("write-qualification-status.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class QualificationStatusTests(unittest.TestCase):
    def test_failure_is_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "evidence" / "status.json"
            result = module.write_status(path, "audio_integrity", 7)
            self.assertEqual(result["status"], "failure")
            self.assertEqual(json.loads(path.read_text())["exit_code"], 7)
            self.assertIsNotNone(datetime.fromisoformat(result["recorded_utc"]).tzinfo)

    def test_complete_success_is_recorded(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "status.json"
            result = module.write_status(path, "complete", 0)
            self.assertEqual(result["status"], "success")

    def test_invalid_stages_do_not_replace_previous_status(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "status.json"
            module.write_status(path, "complete", 0)
            prior = path.read_bytes()
            with self.assertRaises(ValueError):
                module.write_status(path, "unknown", 1)
            with self.assertRaises(ValueError):
                module.write_status(path, "complete", 1)
            self.assertEqual(path.read_bytes(), prior)

if __name__ == "__main__":
    unittest.main()

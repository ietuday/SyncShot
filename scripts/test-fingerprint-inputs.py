import importlib.util
import tempfile
import unittest
from pathlib import Path

script = Path(__file__).with_name("fingerprint-inputs.py")
spec = importlib.util.spec_from_file_location("fingerprint_inputs", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FingerprintTests(unittest.TestCase):
    def test_content_change_modifies_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            f = root / "source.txt"
            f.write_text("one", encoding="utf-8")
            first = module.fingerprint([str(root)])
            self.assertEqual(first["files"], 1)
            self.assertEqual(first["bytes"], 3)
            self.assertEqual(first, module.fingerprint([str(root)]))
            f.write_text("two", encoding="utf-8")
            self.assertNotEqual(first["fingerprint"], module.fingerprint([str(root)])["fingerprint"])

    def test_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                module.fingerprint([str(Path(temp) / "missing")])

if __name__ == "__main__":
    unittest.main()

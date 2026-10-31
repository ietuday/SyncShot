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

    def test_equivalent_directories_are_path_independent(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            left, right = base / "machine-a", base / "machine-b"
            for root in (left, right):
                (root / "nested").mkdir(parents=True)
                (root / "nested" / "image.png").write_bytes(b"same-bytes")
            self.assertEqual(
                module.fingerprint([str(left)])["fingerprint"],
                module.fingerprint([str(right)])["fingerprint"],
            )
            (right / "nested" / "image.png").write_bytes(b"different")
            self.assertNotEqual(
                module.fingerprint([str(left)])["fingerprint"],
                module.fingerprint([str(right)])["fingerprint"],
            )

    def test_reject_reordered_input_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / "audio", Path(temp) / "images"
            a.mkdir()
            b.mkdir()
            (a / "sample").write_bytes(b"audio")
            (b / "sample").write_bytes(b"image")
            self.assertNotEqual(
                module.fingerprint([str(a), str(b)])["fingerprint"],
                module.fingerprint([str(b), str(a)])["fingerprint"],
            )

    def test_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                module.fingerprint([str(Path(temp) / "missing")])

if __name__ == "__main__":
    unittest.main()

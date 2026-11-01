import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location("audit",Path(__file__).with_name("audit-qualification-inputs.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class MediaAuditTests(unittest.TestCase):
    def test_valid_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"a.mp3").write_bytes(b"audio")
            (p/"i.png").write_bytes(b"image")
            out=mod.audit([p])
            self.assertEqual((out["audio_file_count"],out["image_file_count"]),(1,1))

    def test_zero_byte_media_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"a.mp3").touch()
            (p/"i.png").write_bytes(b"image")
            with self.assertRaises(ValueError): mod.audit([p])

    def test_missing_audio_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/"i.png").write_bytes(b"image")
            with self.assertRaises(ValueError): mod.audit([p])

    def test_missing_inputs_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): mod.audit([Path(tmp)/"nonexistent"])

if __name__=="__main__":
    unittest.main()

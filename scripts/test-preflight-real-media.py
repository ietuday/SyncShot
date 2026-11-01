#!/usr/bin/env python3
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location("preflight",Path(__file__).with_name("preflight-real-media.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Result:
    def __init__(self, output, code=0):
        self.stdout=output
        self.stderr=""
        self.returncode=code

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.audio=root/"audio";self.audio.mkdir()
        self.images=root/"images";self.images.mkdir()
        self.report=root/"report";self.report.mkdir()
        (self.audio/"voice.wav").write_bytes(b"test")
        (self.images/"image.png").write_bytes(b"test")
    def test_valid_media(self):
        with patch.object(mod.subprocess,"run",side_effect=[Result("3.0\n"),Result("audio\n"),Result("320,180\n")]):
            result=mod.preflight(self.audio,self.images,self.report,0)
        self.assertEqual(result["audio_files"],1)
        self.assertEqual(result["image_files"],1)
    def test_invalid_image_dimensions(self):
        for response in ("0,180\n","invalid\n","320,NaN\n","320,180,1\n"):
            with self.subTest(response=response):
                with patch.object(mod.subprocess,"run",side_effect=[Result("3.0\n"),Result("audio\n"),Result(response)]):
                    with self.assertRaisesRegex(ValueError,"invalid image"):
                        mod.preflight(self.audio,self.images,self.report,0)
    def test_audio_file_without_audio_stream(self):
        with patch.object(mod.subprocess,"run",side_effect=[Result("3.0\n"),Result("")]):
            with self.assertRaisesRegex(ValueError,"no readable audio stream"):
                mod.preflight(self.audio,self.images,self.report,0)
    def test_nan_audio_duration(self):
        with patch.object(mod.subprocess,"run",return_value=Result("nan\n")):
            with self.assertRaisesRegex(ValueError,"nonpositive duration"):
                mod.preflight(self.audio,self.images,self.report,0)
    def test_invalid_disk_threshold(self):
        with patch.object(mod.subprocess,"run",side_effect=[Result("3.0\n"),Result("audio\n"),Result("320,180\n")]):
            with self.assertRaisesRegex(ValueError,"finite and nonnegative"):
                mod.preflight(self.audio,self.images,self.report,float("nan"))
    def test_missing_media(self):
        (self.audio/"voice.wav").unlink()
        with self.assertRaisesRegex(ValueError,"no supported narration"):
            mod.preflight(self.audio,self.images,self.report,0)
        (self.audio/"voice.wav").write_bytes(b"test")
        (self.images/"image.png").unlink()
        with self.assertRaisesRegex(ValueError,"no supported images"):
            mod.preflight(self.audio,self.images,self.report,0)
    def test_insufficient_disk_space(self):
        with patch.object(mod.subprocess,"run",side_effect=[Result("3.0\n"),Result("audio\n"),Result("320,180\n")]):
            with self.assertRaisesRegex(ValueError,"insufficient free disk"):
                mod.preflight(self.audio,self.images,self.report,float("1e100"))
    def test_unreadable_audio(self):
        with patch.object(mod.subprocess,"run",return_value=Result("",code=1)):
            with self.assertRaisesRegex(ValueError,"ffprobe cannot read"):
                mod.preflight(self.audio,self.images,self.report,0)
    def test_unreadable_image(self):
        with patch.object(mod.subprocess,"run",side_effect=[Result("3.0\n"),Result("audio\n"),Result("",code=1)]):
            with self.assertRaisesRegex(ValueError,"invalid image"):
                mod.preflight(self.audio,self.images,self.report,0)
if __name__=="__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location("decode",Path(__file__).with_name("check-qualification-media-decode.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DecodeTests(unittest.TestCase):
    def files(self, path):
        (path/"a.mp3").write_bytes(b"audio")
        (path/"b.png").write_bytes(b"image")

    def test_valid_audio_and_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.files(root)
            def fake_run(args, **kwargs):
                if args[0]=="ffprobe":
                    stream="audio" if args[-1].endswith(".mp3") else "video"
                    return SimpleNamespace(stdout=json.dumps({"streams":[{"codec_type":stream}]}))
                return SimpleNamespace(stdout="")
            with patch.object(mod.subprocess,"run",side_effect=fake_run):
                result=mod.check_media([root])
            self.assertEqual(result["checked_count"],2)

    def test_decoder_failure_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.files(root)
            def fake_run(args,**kwargs):
                if args[0]=="ffprobe":
                    return SimpleNamespace(stdout='{"streams":[{"codec_type":"audio"}]}')
                raise subprocess.CalledProcessError(1,args)
            with patch.object(mod.subprocess,"run",side_effect=fake_run):
                with self.assertRaises(ValueError): mod.check_media([root])

    def test_missing_media_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError): mod.check_media([Path(tmp)/"missing"])

    def test_invalid_timeout(self):
        with self.assertRaises(ValueError): mod.check_media([],0)

if __name__=="__main__":
    unittest.main()

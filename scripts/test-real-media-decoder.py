#!/usr/bin/env python3
"""Exercise media decode preflight against actual FFmpeg-generated and corrupt files."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("decode", Path(__file__).with_name("check-qualification-media-decode.py"))
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)

class RealDecoderFixtureTests(unittest.TestCase):
    def test_valid_media_and_corrupt_image(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            audio = root / "narration.wav"
            image = root / "frame.png"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                            str(audio)], check=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-f", "lavfi", "-i", "color=c=red:s=320x240:r=1",
                            "-frames:v", "1", str(image)], check=True)
            good = decoder.check_media([root], timeout=30)
            self.assertEqual(good["checked_count"], 2)
            image.write_bytes(b"not actually a PNG file")
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                decoder.check_media([root], timeout=30)

if __name__ == "__main__":
    unittest.main()

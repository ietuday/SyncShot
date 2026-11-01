#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location("pilot_audio",Path(__file__).with_name("prepare-pilot-audio.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Tests(unittest.TestCase):
    def test_trim_and_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            original=root/"original.m4a"
            original.write_bytes(b"original")
            plan={"version":1,"audio":str(original),"duration_seconds":30,
                  "scenes":[{"index":1,"start":0,"end":30}]}
            audio=root/"pilot.m4a"
            manifest=root/"pilot-ready.json"
            calls=[]
            def fake(command,check):
                calls.append(command)
                Path(command[-1]).write_bytes(b"pilot")
            def fake_probe(path):
                return 925 if path==original else 30.01
            result=mod.prepare(plan,audio,manifest,runner=fake,probe=fake_probe)
            self.assertTrue(audio.is_file())
            self.assertTrue(manifest.is_file())
            self.assertEqual(result["audio"],str(audio))
            self.assertEqual(original.read_bytes(),b"original")
            self.assertEqual(len(calls),1)
            with self.assertRaises(FileExistsError):
                mod.prepare(plan,audio,manifest,runner=fake,probe=fake_probe)
    def test_reject_long_duration(self):
        with self.assertRaisesRegex(ValueError,"pilot duration"):
            mod.prepare({"version":1,"duration_seconds":925},Path("x"),Path("y"))
    def test_short_audio_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            audio=root/"src.m4a";audio.write_bytes(b"x")
            with self.assertRaisesRegex(ValueError,"shorter"):
                mod.prepare({"version":1,"audio":str(audio),"duration_seconds":30},
                    root/"out.m4a",root/"out.json",probe=lambda _:10)

if __name__=="__main__":unittest.main()

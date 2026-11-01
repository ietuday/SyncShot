#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec=importlib.util.spec_from_file_location("retrieve",Path(__file__).with_name("retrieve-animation-clips.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Client:
    class tasks:
        @staticmethod
        def retrieve(task_id):
            if task_id=="good":
                return SimpleNamespace(status="SUCCEEDED",output=["https://example.com/video.mp4"])
            if task_id=="pending":
                return SimpleNamespace(status="RUNNING",output=None)
            return SimpleNamespace(status="FAILED",failure="model error")

class Tests(unittest.TestCase):
    def test_status_without_download(self):
        manifest={"mode":"submitted","clips":[{"scene":1,"task_id":"good"},{"scene":2,"task_id":"pending"},{"scene":3,"task_id":"failed"}]}
        result=mod.collect(manifest,Client(),Path("/tmp"))
        self.assertEqual([x["status"] for x in result["clips"]],["SUCCEEDED","RUNNING","FAILED"])
        self.assertTrue(result["clips"][0]["download_available"])
        self.assertNotIn("file",result["clips"][0])
    def test_download_is_opt_in(self):
        calls=[]
        def fake(url,dest): calls.append((url,dest))
        with tempfile.TemporaryDirectory() as temp:
            result=mod.collect({"mode":"submitted","clips":[{"scene":1,"task_id":"good"}]},
                               Client(),Path(temp),True,fake)
            self.assertEqual(len(calls),1)
            self.assertTrue(result["clips"][0]["file"].endswith("scene-0001.mp4"))
    def test_bad_manifest(self):
        with self.assertRaisesRegex(ValueError,"submitted"):
            mod.collect({"mode":"preview","clips":[]},Client(),Path("/tmp"))
    def test_invalid_urls(self):
        for url in ("http://example.com/video.mp4","https://127.0.0.1/video.mp4",
                    "https://localhost/video.mp4","file:///tmp/video.mp4"):
            with self.assertRaises(ValueError):
                mod.validate_url(url)
    def test_reject_existing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"clip.mp4"
            path.write_bytes(b"keep")
            with self.assertRaises(FileExistsError):
                mod.download("https://example.com/file.mp4",path)
            self.assertEqual(path.read_bytes(),b"keep")

if __name__=="__main__": unittest.main()

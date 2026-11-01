#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location("monitor", Path(__file__).with_name("monitor-animation-jobs.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class Client:
    def __init__(self):
        self.calls = []
        self.tasks = self
    def retrieve(self, task_id):
        self.calls.append(task_id)
        status = "RUNNING" if len(self.calls) < 2 else "SUCCEEDED"
        return SimpleNamespace(status=status, failure=None)

class Tests(unittest.TestCase):
    def manifest(self):
        return {"mode":"submitted","clips":[{"scene":1,"task_id":"task-a"}]}
    def test_poll_until_success(self):
        client = Client()
        result = module.poll(module.validate_manifest(self.manifest()), client, interval=1, max_checks=3, sleeper=lambda *_:None)
        self.assertTrue(result["complete"])
        self.assertEqual(len(client.calls),2)
    def test_no_retry_submission(self):
        client = Client()
        module.snapshot(module.validate_manifest(self.manifest()), client)
        self.assertEqual(client.calls, ["task-a"])
    def test_duplicate_scene_rejected(self):
        data = self.manifest()
        data["clips"].append({"scene":1,"task_id":"task-b"})
        with self.assertRaisesRegex(ValueError,"duplicate"):
            module.validate_manifest(data)
    def test_status_file_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"status.json"
            module.save_report(path, {"complete":False})
            with self.assertRaises(FileExistsError):
                module.save_report(path, {"complete":True})
    def test_unknown_status_rejected(self):
        class Bad:
            class tasks:
                @staticmethod
                def retrieve(_):
                    return SimpleNamespace(status="WEIRD")
        with self.assertRaisesRegex(ValueError,"unrecognized"):
            module.snapshot(module.validate_manifest(self.manifest()), Bad())

if __name__ == "__main__":
    unittest.main()

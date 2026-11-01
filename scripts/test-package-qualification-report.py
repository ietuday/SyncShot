#!/usr/bin/env python3
import importlib.util
import tarfile
import tempfile
import unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location("bundle",Path(__file__).with_name("package-qualification-report.py"))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Tests(unittest.TestCase):
    def test_excludes_media_logs_and_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"qualification-abc";root.mkdir()
            run=root/"run-abc";run.mkdir()
            (root/"summary.json").write_text('{"status":"passed"}')
            (run/"measurements.csv").write_text("header\\n")
            (run/"run.log").write_text("secret-path")
            (root/"qualified.mp4").write_bytes(b"video")
            (run/"syncshot").write_bytes(b"binary")
            archive=Path(temp)/"diagnostics.tar.gz"
            self.assertEqual(mod.package(root,archive),2)
            with tarfile.open(archive,"r:gz") as file:
                self.assertEqual(sorted(file.getnames()),["benchmark/measurements.csv","summary.json"])
    def test_rejects_ambiguous_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"qualification-abc";root.mkdir()
            (root/"run-a").mkdir();(root/"run-b").mkdir()
            with self.assertRaisesRegex(ValueError,"exactly one"):
                mod.package(root,Path(temp)/"out.tar.gz")
    def test_does_not_overwrite_existing_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"qualification";root.mkdir()
            run=root/"run-test";run.mkdir()
            (root/"summary.json").write_text("{}")
            dest=Path(temp)/"diagnostics.tar.gz"
            dest.write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError,"overwrite"):
                mod.package(root,dest)
            self.assertEqual(dest.read_bytes(),b"existing")
    def test_rejects_symlinked_run_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"qualification";root.mkdir()
            external=Path(temp)/"run-external";external.mkdir()
            (root/"run-link").symlink_to(external,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,"exactly one"):
                mod.package(root,Path(temp)/"bundle.tar.gz")
if __name__=="__main__":unittest.main()

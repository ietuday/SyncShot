#!/usr/bin/env python3
import importlib.util
import tarfile
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("bundle", Path(__file__).with_name("package-qualification-report.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Tests(unittest.TestCase):
    def setup_run(self, temp):
        root = Path(temp) / "qualification"
        root.mkdir()
        run = root / "run-test"
        run.mkdir()
        (root / "summary.json").write_text("{}")
        return root, run

    def test_excludes_media_logs_and_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root, run = self.setup_run(temp)
            (run / "measurements.csv").write_text("header\\n")
            (run / "run.log").write_text("secret-path")
            (root / "qualified.mp4").write_bytes(b"video")
            (run / "syncshot").write_bytes(b"binary")
            archive = Path(temp) / "diagnostics.tar.gz"
            self.assertEqual(mod.package(root, archive), 2)
            with tarfile.open(archive, "r:gz") as bundle:
                self.assertEqual(sorted(bundle.getnames()), ["benchmark/measurements.csv", "summary.json"])

    def test_rejects_ambiguous_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            (root / "run-other").mkdir()
            with self.assertRaisesRegex(ValueError, "exactly one"):
                mod.package(root, Path(temp) / "out.tar.gz")

    def test_does_not_overwrite_existing_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            dest = Path(temp) / "diagnostics.tar.gz"
            dest.write_bytes(b"existing")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                mod.package(root, dest)
            self.assertEqual(dest.read_bytes(), b"existing")

    def test_rejects_symlinked_run_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            (root / "run-link").symlink_to(Path(temp) / "run-test", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked benchmark"):
                mod.package(root, Path(temp) / "bundle.tar.gz")

    def test_rejects_symlinked_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            alias = Path(temp) / "alias"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlinked qualification"):
                mod.package(alias, Path(temp) / "bundle.tar.gz")

    def test_rejects_output_inside_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            with self.assertRaisesRegex(ValueError, "outside"):
                mod.package(root, root / "bundle.tar.gz")

    def test_rejects_output_through_symlinked_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            alias = Path(temp) / "link"
            alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside"):
                mod.package(root, alias / "bundle.tar.gz")

    def test_rejects_symlinked_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            (root / "summary.json").unlink()
            (root / "summary.json").symlink_to("/etc/passwd")
            with self.assertRaisesRegex(ValueError, "symlinked diagnostic"):
                mod.package(root, Path(temp) / "bundle.tar.gz")

    def test_rejects_dangling_symlink_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            dest = Path(temp) / "bundle.tar.gz"
            dest.symlink_to(Path(temp) / "nonexistent")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                mod.package(root, dest)

    def test_rejects_published_destination_race(self):
        with tempfile.TemporaryDirectory() as temp:
            root, _ = self.setup_run(temp)
            dest = Path(temp) / "bundle.tar.gz"
            original_link = mod.os.link
            def race(src, dst, **kwargs):
                dest.write_bytes(b"competitor")
                return original_link(src, dst, **kwargs)
            mod.os.link = race
            try:
                with self.assertRaises(FileExistsError):
                    mod.package(root, dest)
            finally:
                mod.os.link = original_link
            self.assertEqual(dest.read_bytes(), b"competitor")
            self.assertEqual(list(Path(temp).glob(".qualification-*.tar.gz")), [])


if __name__ == "__main__":
    unittest.main()

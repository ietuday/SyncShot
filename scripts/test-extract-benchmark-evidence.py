#!/usr/bin/env python3
"""Archive extraction security regression tests."""
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent / "extract-benchmark-evidence.py"


class ExtractionTests(unittest.TestCase):
    def run_case(self, entries, success):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "case.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                for name, data, kind in entries:
                    info = tarfile.TarInfo(name)
                    if kind == "symlink":
                        info.type = tarfile.SYMTYPE
                        info.linkname = "../../escape"
                        tar.addfile(info)
                    else:
                        content = data.encode()
                        info.size = len(content)
                        tar.addfile(info, io.BytesIO(content))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(archive), str(root / "out")],
                capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, success, result.stderr)
            self.assertFalse((root / "escape").exists())
            if success:
                self.assertTrue((root / "out/run-manifest.json").exists())

    def test_valid(self):
        self.run_case([
            ("paired-qualification-evidence/run-manifest.json", "{}", "file"),
            ("paired-qualification-evidence/paired-performance-comparison.json", "[]", "file"),
        ], True)

    def test_traversal(self):
        self.run_case([
            ("paired-qualification-evidence/run-manifest.json", "{}", "file"),
            ("paired-qualification-evidence/paired-performance-comparison.json", "[]", "file"),
            ("paired-qualification-evidence/../escape", "bad", "file"),
        ], False)

    def test_symlink(self):
        self.run_case([
            ("paired-qualification-evidence/run-manifest.json", "{}", "file"),
            ("paired-qualification-evidence/paired-performance-comparison.json", "[]", "file"),
            ("paired-qualification-evidence/link", "", "symlink"),
        ], False)

    def test_duplicate(self):
        self.run_case([
            ("paired-qualification-evidence/run-manifest.json", "{}", "file"),
            ("paired-qualification-evidence/paired-performance-comparison.json", "[]", "file"),
            ("paired-qualification-evidence/run-manifest.json", "{}", "file"),
        ], False)


if __name__ == "__main__":
    unittest.main()

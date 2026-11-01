#!/usr/bin/env python3
"""Integration-test production qualification reporting without real media."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "scripts/qualify-production-media.sh"

class FailureRecovery(unittest.TestCase):
    def test_failed_benchmark_preserves_status_and_allows_new_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            bindir = base / "bin"
            bindir.mkdir()
            config = base / "config.json"
            config.write_text("{}", encoding="utf-8")
            media = base / "input.mp3"
            media.write_bytes(b"dummy")
            output = base / "video.mp4"
            reports = base / "reports"
            # Executable shims replace costly Go and benchmark rendering.
            go = bindir / "go"
            go.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            go.chmod(0o755)
            bash = bindir / "bash"
            # Keep the true bash interpreter; benchmark script is intercepted by path.
            fake = base / "benchmark.sh"
            fake.write_text("#!/bin/sh\nexit 23\n", encoding="utf-8")
            fake.chmod(0o755)
            env = os.environ.copy()
            env.update({"PATH": f"{bindir}:{env['PATH']}",
                        "SYNC_SHOT_BENCHMARK_INPUTS": str(media),
                        "SYNC_SHOT_BENCHMARK_WORKLOAD_ID": "recovery-fixture"})
            # This test uses a shell-local function to intercept just the benchmark call.
            command = 'function bash() { if [[ "$1" == "scripts/benchmark-long-video.sh" ]]; then return 23; else command bash "$@"; fi; }; export -f bash; command bash "$1" "$2" "$3" "$4"'
            def run():
                return subprocess.run(["bash", "-c", command, "bash", str(ENTRY),
                                       str(config), str(output), str(reports)],
                                      cwd=ROOT, env=env, capture_output=True, text=True)
            for attempt in (1, 2):
                result = run()
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                dirs = sorted(reports.glob("qualification-*"))
                self.assertEqual(len(dirs), attempt)
                status = json.loads(dirs[-1].joinpath("status.json").read_text())
                self.assertEqual(status["stage"], "benchmark")
                self.assertEqual(status["status"], "failure")
                self.assertEqual(status["exit_code"], 23)
                self.assertFalse(output.exists())
            self.assertNotEqual(dirs[0], dirs[1])

if __name__ == "__main__":
    unittest.main()

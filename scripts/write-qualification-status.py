#!/usr/bin/env python3
"""Write a machine-readable qualification result atomically."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile

STAGES = {"media_audit", "media_decode", "input_fingerprint", "config_dry_run", "preflight_summary", "benchmark", "benchmark_summary", "video_quality", "audio_integrity", "complete"}

def write_status(path: Path, stage: str, code: int):
    if stage not in STAGES:
        raise ValueError(f"unknown qualification stage: {stage}")
    if code < 0:
        raise ValueError("exit code must be nonnegative")
    if stage == "complete" and code != 0:
        raise ValueError("complete stage requires a successful exit")
    payload = {"stage": stage, "exit_code": code,
               "status": "success" if code == 0 else "failure",
               "recorded_utc": datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".status-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return payload

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("stage", choices=sorted(STAGES))
    p.add_argument("exit_code", type=int)
    a = p.parse_args()
    write_status(a.output, a.stage, a.exit_code)

if __name__ == "__main__":
    main()

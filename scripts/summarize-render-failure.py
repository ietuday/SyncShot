#!/usr/bin/env python3
"""Write a bounded, non-invasive diagnostic summary for failed benchmark runs."""
import argparse
import json
import re
from pathlib import Path

def summarize(report: Path, code: int) -> dict:
    log = (report / "run.log").read_text(encoding="utf-8", errors="replace")[-65536:]
    memory = report / "process-memory.csv"
    measurements = report / "measurements.csv"
    sigkill = "signal: killed" in log or "signal: killed" in log.lower()
    oom = bool(re.search(r"out of memory: killed process|oom-kill:", log, re.I))
    diagnostics = {
        "exit_code": code,
        "ffmpeg_sigkill_reported": sigkill,
        "kernel_oom_confirmed": oom,
        "possible_memory_pressure": sigkill or oom,
        "process_memory_csv_exists": memory.exists(),
        "measurements_csv_exists": measurements.exists(),
        "suggestions": [],
    }
    if sigkill and not oom:
        diagnostics["suggestions"].append("SIGKILL observed; check sudo journalctl -k for OOM evidence. SIGKILL alone does not establish OOM.")
    if sigkill or oom:
        diagnostics["suggestions"].append("Retry with --memory-mode low --chunk-scenes 1 and monitor free -h.")
    else:
        diagnostics["suggestions"].append("Inspect run.log and measurements.csv for the failed stage and FFmpeg stderr.")
    (report / "failure-diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
    return diagnostics

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("run_directory", type=Path)
    p.add_argument("exit_code", type=int)
    args = p.parse_args()
    result = summarize(args.run_directory, args.exit_code)
    print("Failure diagnostics: " + str(args.run_directory / "failure-diagnostics.json"))
    if result["ffmpeg_sigkill_reported"]:
        print("FFmpeg SIGKILL detected; check system journal to confirm or rule out OOM.")

if __name__ == "__main__":
    main()

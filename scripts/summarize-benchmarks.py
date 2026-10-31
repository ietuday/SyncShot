#!/usr/bin/env python3
"""Summarize real benchmark runs; reject missing/failed measurements."""
import argparse
import csv
import json
from pathlib import Path

REQUIRED = {"start_utc", "elapsed_seconds", "peak_process_tree_rss_kb", "peak_ffmpeg_rss_kb", "exit_code", "output_bytes"}

def summarize(folder: Path):
    measurements = folder / "measurements.csv"
    with measurements.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError(f"{measurements}: incomplete columns")
        rows = list(reader)
    if len(rows) != 1:
        raise ValueError(f"{measurements}: expected exactly one result")
    row = rows[0]
    if int(row["exit_code"]) != 0:
        raise ValueError(f"{folder.name}: benchmark failed ({row['exit_code']})")
    elapsed = float(row["elapsed_seconds"])
    output = int(row["output_bytes"])
    if elapsed < 0 or output <= 0:
        raise ValueError(f"{folder.name}: invalid elapsed time or output size")
    duration_file = folder / "output-duration.txt"
    if not duration_file.exists():
        raise ValueError(f"{folder.name}: video duration missing")
    duration = float(duration_file.read_text(encoding="utf-8").strip())
    if not 0 < duration < float("inf"):
        raise ValueError(f"{folder.name}: invalid duration")
    return {"run": folder.name, "duration_seconds": duration, "elapsed_seconds": elapsed,
            "realtime_factor": round(elapsed / duration, 4),
            "peak_process_tree_rss_kb": int(row["peak_process_tree_rss_kb"]),
            "peak_ffmpeg_rss_kb": int(row["peak_ffmpeg_rss_kb"]),
            "output_bytes": output}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory containing benchmark run-* folders")
    parser.add_argument("--json", type=Path, help="optional JSON summary output")
    args = parser.parse_args()
    folders = sorted(x for x in args.directory.glob("run-*") if x.is_dir())
    if not folders:
        parser.error("no benchmark run-* directories found")
    results = [summarize(x) for x in folders]
    print(json.dumps(results, indent=2))
    if args.json:
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check the latest benchmark measurement for successful rendering and peak FFmpeg RSS."""
import argparse
import csv
from pathlib import Path

def validate(root: Path, max_mib: float) -> None:
    candidates = sorted(root.glob("run-*/measurements.csv"), key=lambda p:p.stat().st_mtime)
    if not candidates:
        raise ValueError("no benchmark measurements found")
    with candidates[-1].open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError("expected exactly one measurement row")
    row = rows[0]
    peak_kib = int(row["peak_ffmpeg_rss_kb"])
    if int(row["exit_code"]) != 0:
        raise ValueError("benchmark render did not succeed")
    if peak_kib <= 0:
        raise ValueError("FFmpeg peak RSS was not recorded")
    if peak_kib > max_mib * 1024:
        raise ValueError(f"FFmpeg peak RSS {peak_kib / 1024:.1f} MiB exceeds {max_mib:.1f} MiB")
    print(f"Benchmark within RSS budget: FFmpeg peak {peak_kib / 1024:.1f} MiB, limit {max_mib:.1f} MiB")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report_dir", type=Path)
    parser.add_argument("--max-ffmpeg-rss-mib", type=float, required=True)
    args = parser.parse_args()
    if args.max_ffmpeg_rss_mib <= 0:
        parser.error("RSS limit must be positive")
    try:
        validate(args.report_dir, args.max_ffmpeg_rss_mib)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f"Memory qualification failed: {exc}\n")

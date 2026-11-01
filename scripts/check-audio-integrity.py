#!/usr/bin/env python3
"""Check that rendered audio decodes and has measurable non-silent content."""
import argparse
import json
import math
import re
import subprocess

def validate(path, min_mean_db=-65.0, min_peak_db=-45.0):
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path),
         "-map", "0:a:0", "-vn", "-af", "volumedetect",
         "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    combined = result.stderr
    mean = re.search(r"mean_volume:\s*(-?(?:\d+(?:\.\d+)?|inf)) dB", combined)
    peak = re.search(r"max_volume:\s*(-?(?:\d+(?:\.\d+)?|inf)) dB", combined)
    if not mean or not peak:
        raise ValueError("audio volume metrics unavailable")
    mean_db, peak_db = float(mean.group(1)), float(peak.group(1))
    if not math.isfinite(mean_db) or not math.isfinite(peak_db):
        raise ValueError("audio is silent or contains invalid levels")
    if mean_db < min_mean_db or peak_db < min_peak_db:
        raise ValueError("rendered audio volume below minimum levels")
    return {"mean_volume_db": mean_db, "peak_volume_db": peak_db,
            "decodable_audio": True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--min-mean-db", type=float, default=-65.0)
    parser.add_argument("--min-peak-db", type=float, default=-45.0)
    args = parser.parse_args()
    print(json.dumps(validate(args.video, args.min_mean_db, args.min_peak_db), indent=2))

if __name__ == "__main__":
    main()

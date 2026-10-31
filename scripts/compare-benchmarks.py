#!/usr/bin/env python3
"""Compare two validated SyncShot benchmark reports."""
import argparse
import json
from pathlib import Path

METRICS = ("realtime_factor", "peak_process_tree_rss_kb", "peak_ffmpeg_rss_kb")

def read_run(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) != 1:
        raise ValueError("Each report must contain exactly one benchmark run")
    run = data[0]
    for key in METRICS:
        value = float(run[key])
        if not 0 < value < float("inf"):
            raise ValueError(f"Invalid {key} in {path}")
    return run

def compare(base, current, limit):
    base_id = base.get("workload_id", "unlabeled")
    current_id = current.get("workload_id", "unlabeled")
    if not base_id or base_id == "unlabeled" or current_id != base_id:
        raise ValueError("matching labeled workload_id is required for valid comparisons")
    base_fp = base.get("input_fingerprint", "unknown")
    candidate_fp = current.get("input_fingerprint", "unknown")
    if (not isinstance(base_fp, str) or not isinstance(candidate_fp, str)
            or len(base_fp) != 64 or len(candidate_fp) != 64
            or any(ch not in "0123456789abcdef" for ch in base_fp + candidate_fp)):
        raise ValueError("both benchmarks require valid SHA-256 input fingerprints")
    if base_fp != candidate_fp:
        raise ValueError("benchmark inputs differ; cannot compare mismatched media")
    rows = []
    failed = False
    for key in METRICS:
        before = float(base[key])
        after = float(current[key])
        percent = (after - before) / before * 100
        is_regression = percent > limit
        failed |= is_regression
        rows.append({"metric": key, "baseline": before, "candidate": after,
                     "change_pct": round(percent, 2), "regression": is_regression})
    return rows, failed

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--max-regression-percent", type=float, default=15)
    args = parser.parse_args()
    if not 0 <= args.max_regression_percent < float("inf"):
        parser.error("regression threshold must be finite and nonnegative")
    rows, failed = compare(read_run(args.baseline), read_run(args.candidate),
                           args.max_regression_percent)
    print(json.dumps(rows, indent=2))
    if failed:
        parser.exit(1, "Benchmark performance regression detected\n")

if __name__ == "__main__":
    main()

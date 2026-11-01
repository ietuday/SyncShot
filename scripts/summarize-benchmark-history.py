#!/usr/bin/env python3
"""Summarize archived SyncShot qualification evidence without fabricating missing runs."""
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone

METRICS = ("realtime_factor", "peak_process_tree_rss_kb", "peak_ffmpeg_rss_kb")


def collect(directory):
    manifest_path = directory / "run-manifest.json"
    comparison_path = directory / "paired-performance-comparison.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = json.loads(comparison_path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or len(rows) != 3:
        raise ValueError(f"{directory}: expected three comparison metrics")
    by_metric = {row["metric"]: row for row in rows}
    if set(by_metric) != set(METRICS):
        raise ValueError(f"{directory}: unexpected metric set")
    for metric in METRICS:
        row = by_metric[metric]
        if any(not isinstance(row.get(key), (int, float)) or
               isinstance(row.get(key), bool) for key in ("baseline", "candidate", "change_pct")):
            raise ValueError(f"{directory}: invalid numeric values for {metric}")
    for key in ("baseline_commit", "candidate_commit", "workload_id"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise ValueError(f"{directory}: missing {key}")
    return {
        "evidence_directory": str(directory),
        "baseline_commit": manifest["baseline_commit"],
        "candidate_commit": manifest["candidate_commit"],
        "workload_id": manifest["workload_id"],
        "mode": manifest.get("mode", "unknown"),
        "repetitions_per_side": manifest.get("repetitions_per_side"),
        "metrics": {key: by_metric[key] for key in METRICS},
    }


def markdown(records):
    lines = ["# SyncShot benchmark history", "",
             "Entries are ordered by provided evidence directory, not measurement date.",
             "Comparisons are not a controlled performance certification.", "",
             "| Evidence | Baseline | Candidate | Workload | Realtime factor change | Process RSS change | FFmpeg RSS change |",
             "| --- | --- | --- | --- | ---: | ---: | ---: |"]
    for row in records:
        changes = [f'{row["metrics"][metric]["change_pct"]:+.2f}%'
                   for metric in METRICS]
        def cell(value):
            return str(value).replace("|", "\\|").replace("\n", " ")
        lines.append("| " + " | ".join(map(cell, [
            row["evidence_directory"], row["baseline_commit"][:12],
            row["candidate_commit"][:12], row["workload_id"], *changes])) + " |")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, nargs="+", help="Unpacked evidence folders")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    records = [collect(path) for path in args.evidence]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "history.json").write_text(
        json.dumps({"schema_version": 1, "records": records}, indent=2) + "\n",
        encoding="utf-8")
    (args.output_dir / "history.md").write_text(markdown(records), encoding="utf-8")


if __name__ == "__main__":
    main()

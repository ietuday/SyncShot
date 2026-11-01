#!/usr/bin/env python3
"""Summarize archived SyncShot qualification evidence without fabricating missing runs."""
import argparse
import json
import math
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
        if not all(math.isfinite(row[key]) for key in ("baseline", "candidate", "change_pct")):
            raise ValueError(f"{directory}: nonfinite metric for {metric}")
    for key in ("baseline_commit", "candidate_commit", "workload_id"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise ValueError(f"{directory}: missing {key}")
    return {
        "evidence_directory": str(directory),
        "baseline_commit": manifest["baseline_commit"],
        "candidate_commit": manifest["candidate_commit"],
        "workload_id": manifest["workload_id"],
        "mode": manifest.get("mode", "unknown"),
        "environment": manifest.get("environment"),
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



def trend_csv(records):
    """Long-form comparison data; input order is not a timestamp."""
    import csv
    import io
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(("sequence", "workload_id", "baseline_commit", "candidate_commit",
                     "metric", "baseline", "candidate", "change_pct"))
    for sequence, record in enumerate(records, 1):
        for metric in METRICS:
            row = record["metrics"][metric]
            writer.writerow((sequence, record["workload_id"], record["baseline_commit"],
                             record["candidate_commit"], metric,
                             row["baseline"], row["candidate"], row["change_pct"]))
    return buffer.getvalue()


def trend_svg(records):
    """Dependency-free SVG of percentage changes in the provided evidence order."""
    from html import escape
    width, height = 980, 440
    left, right, top, bottom = 90, 30, 60, 75
    values = [row["metrics"][m]["change_pct"] for row in records for m in METRICS]
    low, high = min([0, *values]), max([0, *values])
    margin = max(5.0, (high - low) * 0.1)
    low, high = low - margin, high + margin
    plot_w, plot_h = width - left - right, height - top - bottom
    def x(index):
        return left + plot_w * (index / max(1, len(records) - 1))
    def y(value):
        return top + plot_h * (high - value) / (high - low)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<text x="90" y="28" font-size="20">Benchmark comparison changes by evidence order</text>',
             f'<line x1="{left}" y1="{y(0):.1f}" x2="{width-right}" y2="{y(0):.1f}" stroke="#777" stroke-dasharray="5 5"/>']
    palette = ("#1769aa", "#c35424", "#26845b")
    for k, metric in enumerate(METRICS):
        points = [(x(i), y(rec["metrics"][metric]["change_pct"]))
                  for i, rec in enumerate(records)]
        path = " ".join(f'{px:.1f},{py:.1f}' for px, py in points)
        parts.append(f'<polyline points="{path}" fill="none" stroke="{palette[k]}" stroke-width="2.5"/>')
        for px, py in points:
            parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{palette[k]}"/>')
        parts.append(f'<text x="{left + k*290}" y="{height-12}" font-size="13" fill="{palette[k]}">{escape(metric)}</text>')
    for i in range(len(records)):
        parts.append(f'<text x="{x(i):.1f}" y="{height-bottom+23}" font-size="12" text-anchor="middle">{i+1}</text>')
    parts.append(f'<text x="12" y="{top+12}" font-size="12">{high:+.1f}%</text>')
    parts.append(f'<text x="12" y="{height-bottom}" font-size="12">{low:+.1f}%</text>')
    parts.append(f'<text x="{left}" y="{height-45}" font-size="12">Sequence follows input order, not time. Compare only compatible workloads.</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"



def regressions(records, threshold):
    """Flag comparisons above a configured limit; never compare unrelated runs."""
    alerts = []
    for record in records:
        for metric in METRICS:
            row = record["metrics"][metric]
            if row["change_pct"] > threshold:
                alerts.append({
                    "evidence_directory": record["evidence_directory"],
                    "workload_id": record["workload_id"],
                    "baseline_commit": record["baseline_commit"],
                    "candidate_commit": record["candidate_commit"],
                    "metric": metric,
                    "change_pct": row["change_pct"],
                    "threshold_pct": threshold,
                })
    return alerts


def alert_markdown(alerts, threshold):
    """Render actionable warnings without assuming cross-run comparability."""
    lines = ["# SyncShot benchmark regression alerts", "",
             f"Configured threshold: {threshold:g}%", ""]
    if not alerts:
        lines.extend(["No metric exceeded the configured threshold.", ""])
    else:
        lines.extend(["| Evidence | Workload | Metric | Change | Baseline | Candidate |",
                      "| --- | --- | --- | ---: | --- | --- |"])
        for item in alerts:
            def escape_cell(value):
                return str(value).replace("|", "\\|").replace("\\n", " ")
            cells = (item["evidence_directory"], item["workload_id"],
                     item["metric"], f'{item["change_pct"]:+.2f}%',
                     item["baseline_commit"][:12], item["candidate_commit"][:12])
            lines.append("| " + " | ".join(escape_cell(v) for v in cells) + " |")
        lines.append("")
    lines.extend(["This flags CI evidence only; validate workload, media and runner equivalence.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path, nargs="+", help="Unpacked evidence folders")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--alert-threshold-percent", type=float, default=200,
                        help="Positive regression percent triggering nonzero exit")
    parser.add_argument("--require-workload-id", default=None,
                        help="Reject evidence with other workload IDs")
    parser.add_argument("--min-repetitions", type=int, default=1,
                        help="Minimum qualification runs per side")
    parser.add_argument("--require-matching-inputs", action="store_true",
                        help="Require matching workload and input fingerprints across evidence")
    parser.add_argument("--require-matching-environment", action="store_true",
                        help="Require consistent runner/platform/config provenance for all records")
    args = parser.parse_args()
    if args.min_repetitions < 1:
        parser.error("min-repetitions must be positive")
    if not math.isfinite(args.alert_threshold_percent) or args.alert_threshold_percent < 0:
        parser.error("alert threshold must be finite and nonnegative")
    records = [collect(path) for path in args.evidence]
    for record in records:
        if args.require_workload_id and record["workload_id"] != args.require_workload_id:
            parser.error("workload mismatch in " + record["evidence_directory"])
        runs = record["repetitions_per_side"]
        if not isinstance(runs, int) or isinstance(runs, bool) or runs < args.min_repetitions:
            parser.error("insufficient repetitions in " + record["evidence_directory"])
    if args.require_matching_environment:
        first = records[0]["environment"]
        required = ("system", "machine", "python", "runner_image",
                    "runner_arch", "config_sha256", "ffmpeg_version",
                    "go_version", "cpu_model")
        if not isinstance(first, dict) or any(not first.get(key) or first[key] == "unknown" for key in required):
            parser.error("environment provenance missing or incomplete")
        for record in records[1:]:
            env = record["environment"]
            if not isinstance(env, dict) or any(env.get(key) != first[key] for key in required):
                parser.error("benchmark environment mismatch")
    if args.require_matching_inputs:
        fingerprints = []
        for directory in args.evidence:
            manifest = json.loads((directory / "run-manifest.json").read_text(encoding="utf-8"))
            reports = manifest.get("baseline", []) + manifest.get("candidate", [])
            if not reports:
                parser.error("missing referenced qualification reports in " + str(directory))
            found = set()
            for name in reports:
                path = directory / name
                if not path.is_file() or path.parent != directory:
                    parser.error("missing or invalid qualification report " + str(name))
                raw = json.loads(path.read_text(encoding="utf-8"))
                runs = raw if isinstance(raw, list) else [raw]
                for item in runs:
                    fingerprint = item.get("input_fingerprint") if isinstance(item, dict) else None
                    if not isinstance(fingerprint, str) or not fingerprint:
                        parser.error("input fingerprint missing in " + str(path))
                    found.add(fingerprint)
            if len(found) != 1:
                parser.error("input fingerprint drift within " + str(directory))
            fingerprints.append((records[len(fingerprints)]["workload_id"], found.pop()))
        if len(set(fingerprints)) != 1:
            parser.error("benchmark workload/input drift between evidence directories")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "history.json").write_text(
        json.dumps({"schema_version": 1, "records": records}, indent=2) + "\n",
        encoding="utf-8")
    (args.output_dir / "history.md").write_text(markdown(records), encoding="utf-8")
    (args.output_dir / "trend.csv").write_text(trend_csv(records), encoding="utf-8")
    (args.output_dir / "trend.svg").write_text(trend_svg(records), encoding="utf-8")
    alerts = regressions(records, args.alert_threshold_percent)
    (args.output_dir / "regression-alerts.json").write_text(
        json.dumps({"threshold_percent": args.alert_threshold_percent,
                    "alerts": alerts}, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "regression-alerts.md").write_text(
        alert_markdown(alerts, args.alert_threshold_percent), encoding="utf-8")
    if alerts:
        print(f"Found {len(alerts)} benchmark regressions", file=__import__("sys").stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

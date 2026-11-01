#!/usr/bin/env python3
"""Create a concise JSON and Markdown summary of one isolated benchmark run."""
import argparse
import csv
import json
from pathlib import Path

def summarize(report: Path) -> dict:
    runs=list(report.glob("run-*/measurements.csv"))
    if len(runs)!=1:
        raise ValueError(f"expected exactly one benchmark, found {len(runs)}")
    run=runs[0].parent
    with runs[0].open(newline="") as stream:
        records=list(csv.DictReader(stream))
    if len(records)!=1:
        raise ValueError("expected one benchmark measurement record")
    row=records[0]
    result={
        "status":"passed" if int(row["exit_code"])==0 else "failed",
        "exit_code":int(row["exit_code"]),
        "elapsed_seconds":int(row["elapsed_seconds"]),
        "peak_ffmpeg_rss_mib":round(int(row["peak_ffmpeg_rss_kb"])/1024,2),
        "peak_process_tree_rss_mib":round(int(row["peak_process_tree_rss_kb"])/1024,2),
        "output_bytes":int(row["output_bytes"]),
        "benchmark_report":run.name,
    }
    (report/"summary.json").write_text(json.dumps(result,indent=2)+"\n")
    text=("# SyncShot Qualification Summary\n\n"+
          f"- Status: **{result['status']}** (exit {result['exit_code']})\n"+
          f"- Duration: {result['elapsed_seconds']} seconds\n"+
          f"- Peak FFmpeg RSS: {result['peak_ffmpeg_rss_mib']} MiB\n"+
          f"- Peak process-tree RSS: {result['peak_process_tree_rss_mib']} MiB\n"+
          f"- Output bytes: {result['output_bytes']}\n"+
          f"- Benchmark details: {run.name}/\n")
    (report/"summary.md").write_text(text)
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("report",type=Path)
    args=parser.parse_args()
    try:
        result=summarize(args.report)
    except (ValueError,OSError,KeyError) as err:
        parser.exit(1,f"Cannot summarize benchmark: {err}\n")
    print(json.dumps(result,indent=2))

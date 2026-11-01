#!/usr/bin/env python3
"""Classify benchmark and validation failures without asserting unobserved OOM."""
import argparse
import json
from pathlib import Path

def analyze(report: Path, stage: str, exit_code: int) -> dict:
    runs=list(report.glob("run-*"))
    category="unknown"
    notes=[]
    if stage=="benchmark":
        category="render_failure"
        if len(runs)==1:
            log=runs[0]/"run.log"
            body=log.read_text(encoding="utf-8",errors="replace")[-65536:].lower() if log.exists() else ""
            if "signal: killed" in body:
                category="ffmpeg_sigkill"
                notes.append("SIGKILL observed; check sudo journalctl -k to determine whether the kernel OOM killer was involved.")
            else:
                notes.append("Review run.log and failure-diagnostics.json for the FFmpeg error.")
    elif stage=="memory":
        category="memory_budget_exceeded"
        notes.append("Review measurements.csv; test RSS ceiling is not a process memory limit.")
    elif stage=="av_sync":
        category="stream_timing_mismatch"
        notes.append("Check audio/video stream endpoints with ffprobe.")
    elif stage=="dimensions":
        category="unexpected_video_dimensions"
        notes.append("Expected 1280x720; inspect ffprobe stream dimensions.")
    else:
        notes.append("Review qualification logs and report directory.")
    result={"category":category,"stage":stage,"exit_code":exit_code,"notes":notes}
    (report/"failure-analysis.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("report",type=Path)
    parser.add_argument("stage")
    parser.add_argument("exit_code",type=int)
    args=parser.parse_args()
    print(json.dumps(analyze(args.report,args.stage,args.exit_code),indent=2))

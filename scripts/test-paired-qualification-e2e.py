#!/usr/bin/env python3
"""Run paired complete qualification on the same synthetic inputs and compare evidence."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent

def run(*args, env=None):
    subprocess.run(args, cwd=ROOT, env=env, check=True)

def main():
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        (work / "images").mkdir()
        (work / "audio").mkdir()
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "testsrc2=size=1280x720:rate=1", "-frames:v", "1",
            str(work / "images/001.png"))
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "smptebars=size=1280x720:rate=1", "-frames:v", "1",
            str(work / "images/002.png"))
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=6", "-c:a", "libmp3lame",
            str(work / "audio/narration.mp3"))
        config = work / "config.json"
        config.write_text(json.dumps({
            "AudioDir": str(work / "audio"), "ImagesDir": str(work / "images"),
            "OutVideoPath": str(work / "first.mp4"),
            "OutShortsDir": str(work / "shorts"), "WorkDir": str(work / "work"),
            "ClipSeconds": 0, "RenderProfile": "720p", "MaxWorkers": 2,
            "CinematicChunkScenes": 4
        }), encoding="utf-8")
        env = os.environ.copy()
        env.update({
            "SYNC_SHOT_BENCHMARK_WORKLOAD_ID": "paired-qualification-6s-720p",
            "SYNC_SHOT_BENCHMARK_INPUTS": ":".join((
                str(work / "audio"), str(work / "images"), str(config))),
            "SYNC_SHOT_EXPECT_WIDTH": "1280",
            "SYNC_SHOT_EXPECT_HEIGHT": "720",
            "SYNC_SHOT_MIN_DURATION": "4",
            "SYNC_SHOT_MAX_DURATION": "9",
            "SYNC_SHOT_QUALIFICATION_TIMEOUT": "8m"
        })
        reports = []
        for suffix in ("baseline", "candidate"):
            report_root = work / suffix
            run("bash", "scripts/qualify-production-media.sh", str(config),
                str(work / (suffix + ".mp4")), str(report_root), env=env)
            matches = list(report_root.glob("qualification-*/qualification-summary.json"))
            if len(matches) != 1:
                raise RuntimeError(f"{suffix}: missing or duplicate qualification report")
            reports.append(matches[0])
        comparison = subprocess.run(
            [sys.executable, "scripts/compare-benchmarks.py", str(reports[0]),
             str(reports[1]), "--max-regression-percent", "200"],
            cwd=ROOT, capture_output=True, text=True, check=True)
        rows = json.loads(comparison.stdout)
        if len(rows) != 3 or any(row["regression"] for row in rows):
            raise RuntimeError("incomplete or failing comparison")
        evidence = os.environ.get("SYNC_SHOT_BENCHMARK_EVIDENCE_DIR")
        if evidence:
            dest = Path(evidence).resolve()
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "paired-performance-comparison.json").write_text(
                json.dumps(rows, indent=2) + "\n", encoding="utf-8")
            for name, path in zip(("baseline", "candidate"), reports):
                (dest / (name + "-qualification-summary.json")).write_bytes(path.read_bytes())
        print("Paired qualification comparison passed (wide 200% CI noise allowance)")

if __name__ == "__main__":
    main()

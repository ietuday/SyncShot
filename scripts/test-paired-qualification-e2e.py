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


def check_comparator_contract():
    """Exercise expected comparator failures without running an expensive render."""
    import runpy
    comparator = runpy.run_path(str(ROOT / "scripts/compare-benchmarks.py"))
    compare = comparator["compare"]
    read_run = comparator["read_run"]
    baseline = {
        "workload_id": "synthetic-test",
        "input_fingerprint": "a" * 64,
        "realtime_factor": 1.0,
        "peak_process_tree_rss_kb": 100.0,
        "peak_ffmpeg_rss_kb": 50.0,
    }
    rows, failed = compare(baseline, dict(baseline), 15)
    assert len(rows) == 3 and not failed
    changed = dict(baseline, realtime_factor=1.16)
    rows, failed = compare(baseline, changed, 15)
    assert failed and rows[0]["regression"] and not rows[1]["regression"]
    rows, failed = compare(baseline, dict(baseline, peak_ffmpeg_rss_kb=57.5), 15)
    assert not failed, "exactly 15 percent must pass"
    for changed in (
        dict(baseline, workload_id="different"),
        dict(baseline, input_fingerprint="b" * 64),
        dict(baseline, input_fingerprint="invalid"),
    ):
        try:
            compare(baseline, changed, 200)
        except ValueError:
            pass
        else:
            raise AssertionError("comparator accepted incompatible benchmark")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "invalid.json"
        for invalid in (0, -1, "nan", "inf"):
            path.write_text(json.dumps([dict(baseline, realtime_factor=invalid)]),
                            encoding="utf-8")
            try:
                read_run(path)
            except ValueError:
                pass
            else:
                raise AssertionError(f"comparator accepted invalid metric: {invalid}")
    print("Benchmark comparator contract checks passed")

def check_median_contract():
    """Verify robust aggregation and input equivalence before rendering."""
    import runpy
    module = runpy.run_path(str(ROOT / "scripts/compare-benchmarks.py"))
    aggregate = module["aggregate_reports"]
    compare = module["compare"]
    template = {
        "workload_id": "median-contract",
        "input_fingerprint": "a" * 64,
        "realtime_factor": 1.0,
        "peak_process_tree_rss_kb": 100.0,
        "peak_ffmpeg_rss_kb": 50.0,
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        def make(name, **changes):
            path = root / (name + ".json")
            path.write_text(json.dumps([dict(template, **changes)]), encoding="utf-8")
            return path
        baseline = aggregate([make("base1"), make("base2", realtime_factor=1.1),
                              make("base3", realtime_factor=10)])
        candidate = aggregate([make("cand1", realtime_factor=1.2),
                               make("cand2", realtime_factor=1.3),
                               make("cand3", realtime_factor=12)])
        assert baseline["realtime_factor"] == 1.1
        assert candidate["realtime_factor"] == 1.3
        rows, failed = compare(baseline, candidate, 15)
        assert failed and rows[0]["regression"], "median regression should fail"
        bad = make("bad", input_fingerprint="b" * 64)
        try:
            aggregate([make("good"), bad])
        except ValueError:
            pass
        else:
            raise AssertionError("aggregation accepted different input media")
    print("Median comparator contract checks passed")

def main():
    check_comparator_contract()
    check_median_contract()
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

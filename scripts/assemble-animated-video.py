#!/usr/bin/env python3
"""Assemble downloaded animated scenes with their original narration using FFmpeg.

Scenes must fully cover the narration timeline without gaps or overlaps.
Each source clip loops or trims to fit its scene. Output is published without overwriting.
"""
import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path

MAX_SCENES = 1000


def validate_plan(data, clips_dir):
    if data.get("version") != 1 or not isinstance(data.get("scenes"), list):
        raise ValueError("expected Phase 9 scene plan version 1")
    duration = data.get("duration_seconds")
    if not isinstance(duration, (float, int)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid narration duration")
    scenes = data["scenes"]
    if not 1 <= len(scenes) <= MAX_SCENES:
        raise ValueError("scene count must be 1..1000")
    previous = 0.0
    result = []
    for index, scene in enumerate(scenes, 1):
        start, end = scene.get("start"), scene.get("end")
        if (scene.get("index") != index or not isinstance(start, (int, float))
                or not isinstance(end, (int, float)) or not math.isfinite(start)
                or not math.isfinite(end) or abs(start - previous) > 0.02
                or end <= start):
            raise ValueError(f"scene {index} has gaps, overlaps or invalid timestamps")
        path = clips_dir / f"scene-{index:04d}.mp4"
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or symlinked animation clip: {path}")
        result.append((path, end - start))
        previous = end
    if abs(previous - duration) > 0.02:
        raise ValueError("scene timeline must cover full narration duration")
    return result, duration


def ffmpeg(command, runner=subprocess.run):
    runner(command, check=True)


def build_commands(clips, audio, workdir, output, fps=24):
    segments = []
    for index, (clip, seconds) in enumerate(clips, 1):
        target = workdir / f"segment-{index:04d}.mp4"
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-stream_loop", "-1", "-i", str(clip), "-t", f"{seconds:.6f}",
                   "-vf", f"fps={fps},scale=1280:720:force_original_aspect_ratio=decrease,"
                          "pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                   "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                   "-threads", "2", "-pix_fmt", "yuv420p", str(target)]
        segments.append((command, target))
    manifest = workdir / "concat.txt"
    # ffconcat files are controlled output paths in a fresh private work directory.
    final = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
             "-f", "concat", "-safe", "0", "-i", str(manifest),
             "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
             "-movflags", "+faststart", str(output)]
    return segments, manifest, final


def assemble(plan, clips_dir, output, runner=subprocess.run):
    clips, _duration = validate_plan(plan, clips_dir)
    audio = Path(plan.get("audio", ""))
    if not audio.is_file():
        raise ValueError(f"narration audio not found: {audio}")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"refusing to overwrite {output}")
    if not output.parent.is_dir():
        raise ValueError("output parent directory must exist")
    with tempfile.TemporaryDirectory(prefix=".animation-assembly-", dir=output.parent) as temp:
        workdir = Path(temp)
        staging = workdir / "final.mp4"
        segments, manifest, final = build_commands(clips, audio, workdir, staging)
        for command, _ in segments:
            ffmpeg(command, runner)
        with manifest.open("w", encoding="utf-8") as file:
            for _, segment in segments:
                # File paths use controlled tempfile directory; escape any single quotes.
                path = str(segment.resolve()).replace("'", "'\\''")
                file.write(f"file '{path}'\n")
        ffmpeg(final, runner)
        if not staging.is_file() or staging.stat().st_size == 0:
            raise ValueError("assembled output is missing or empty")
        os.link(staging, output)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--clips-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.plan.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("scene plan is too large")
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        assemble(plan, args.clips_dir, args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Animation assembly failed: {error}\n")
    print(f"Created narration-aligned animation video: {args.output}")


if __name__ == "__main__":
    main()

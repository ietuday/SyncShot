#!/usr/bin/env python3
"""Guided, resumable animation pipeline. Paid generation is never automatic."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

STAGES = ("transcribe", "plan", "preview-images", "preview-animation", "retrieve", "assemble")
def command_for(stage, args, root):
    python = sys.executable
    if stage == "transcribe":
        return [python, str(root/"scripts/transcribe-audio.py"), "--audio", str(args.audio),
                "--output", str(args.workdir/"transcript.json"), "--language", args.language,
                "--model", args.model]
    if stage == "plan":
        return ["go", "run", "./cmd/storyplan", "--transcript", str(args.workdir/"transcript.json"),
                "--output", str(args.workdir/"scene-plan.json"), "--style", args.style,
                "--scene-seconds", str(args.scene_seconds)]
    if stage == "preview-images":
        return [python, str(root/"scripts/generate-scene-images.py"),
                "--plan", str(args.workdir/"scene-plan.json"), "--output-dir",
                str(args.workdir/"images"), "--limit", str(args.limit)]
    if stage == "preview-animation":
        return [python, str(root/"scripts/animate-scene-images.py"), "--plan",
                str(args.workdir/"scene-plan.json"), "--image-urls", str(args.image_urls),
                "--output", str(args.workdir/"animation-preview.json"), "--limit", str(args.limit)]
    if stage == "retrieve":
        return [python, str(root/"scripts/retrieve-animation-clips.py"), "--tasks",
                str(args.tasks), "--output-dir", str(args.clips_dir),
                "--report", str(args.workdir/"task-status.json")]
    return [python, str(root/"scripts/assemble-animated-video.py"), "--plan",
            str(args.workdir/"scene-plan.json"), "--clips-dir", str(args.clips_dir),
            "--output", str(args.output)]

def run(args, runner=subprocess.run):
    root = Path(__file__).resolve().parent.parent
    if args.scene_seconds <= 0 or args.limit < 1 or args.limit > 100:
        raise ValueError("scene-seconds must be positive and limit must be 1..100")
    if args.stage in ("preview-animation",) and not args.image_urls:
        raise ValueError("--image-urls required for animation preview")
    if args.stage == "retrieve" and not args.tasks:
        raise ValueError("--tasks required for task retrieval")
    if args.stage == "assemble" and (not args.clips_dir or not args.output):
        raise ValueError("--clips-dir and --output required for assembly")
    args.workdir.mkdir(parents=True, exist_ok=True)
    command = command_for(args.stage, args, root)
    # No --execute or --download flags are ever forwarded.
    runner(command, check=True, cwd=root)
    return command

def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", required=True, choices=STAGES)
    p.add_argument("--audio", type=Path)
    p.add_argument("--workdir", type=Path, default=Path("output/animation-workflow"))
    p.add_argument("--language", choices=("auto","hi","en"), default="auto")
    p.add_argument("--model", choices=("tiny","base","small"), default="tiny")
    p.add_argument("--style", choices=("mythological_3d","cartoon_2d","cinematic_realistic"), default="mythological_3d")
    p.add_argument("--scene-seconds", type=float, default=8)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--image-urls", type=Path)
    p.add_argument("--tasks", type=Path)
    p.add_argument("--clips-dir", type=Path)
    p.add_argument("--output", type=Path)
    return p

def main():
    p = parser()
    args = p.parse_args()
    if args.stage == "transcribe" and not args.audio:
        p.error("--audio required for transcribe")
    try:
        run(args)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1, f"Animation workflow failed: {exc}\n")

if __name__ == "__main__":
    main()

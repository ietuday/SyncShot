#!/usr/bin/env python3
"""Verify a single downloaded animation clip and assemble its narration-aligned demo MP4."""
import argparse
import importlib.util
import json
import os
import tempfile
import subprocess
from pathlib import Path

def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

verify = module("verify-provider-clip.py", "provider_verify")
assemble = module("assemble-animated-video.py", "animation_assembly")

def build_demo(plan, clips_dir, output, report, verifier=verify.verify,
               probe=verify.ffprobe, assembler=assemble.assemble):
    if output.exists() or output.is_symlink() or report.exists() or report.is_symlink():
        raise FileExistsError("output MP4 or verification report already exists")
    if not output.parent.is_dir() or not report.parent.is_dir():
        raise ValueError("output and report parent directories must already exist")
    clip = clips_dir / "scene-0001.mp4"
    info = verifier(plan, clip, probe)
    audio = Path(plan.get("audio", ""))
    if not audio.is_file() or audio.is_symlink():
        raise ValueError("narration audio is missing or a symlink")
    if output == report:
        raise ValueError("report and video paths cannot match")
    # Reserve the report before rendering so an unavailable report destination
    # cannot leave an unreported published video. Publish report atomically.
    with tempfile.TemporaryDirectory(prefix=".provider-report-",dir=report.parent) as tmp:
        stage = Path(tmp) / "report.json"
        with stage.open("x", encoding="utf-8") as file:
            json.dump({**info,"video_output":str(output)}, file,ensure_ascii=False,indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        assembler(plan, clips_dir, output)
        try:
            os.link(stage,report)
        except Exception:
            # Never destroy a finished video if the report cannot publish;
            # explicit recovery can reconstruct the report later.
            raise
    info["video_output"] = str(output)
    return info

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--clips-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.plan.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("scene plan too large")
        info = build_demo(json.loads(args.plan.read_text(encoding="utf-8")),
                          args.clips_dir, args.output, args.report)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1, f"Provider demo failed: {exc}\n")
    print(f"Created demo video: {info['video_output']}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Prepare a one-scene Runway pilot request. Never submits API requests."""
import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

def build(plan, image_url):
    if plan.get("version") != 1 or not plan.get("pilot_audio_prepared"):
        raise ValueError("provide a prepared Phase 9 pilot-ready plan")
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("no pilot scenes")
    scene = scenes[0]
    if scene.get("index") != 1 or not isinstance(scene.get("visual_prompt"), str) or not scene["visual_prompt"].strip():
        raise ValueError("invalid first scene")
    url = urlsplit(image_url)
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        raise ValueError("hosted image must use HTTPS without embedded credentials")
    duration = scene.get("end")
    if not isinstance(duration, (float, int)) or isinstance(duration, bool) or not math.isfinite(duration) or not 0 < duration <= 120:
        raise ValueError("invalid first-scene duration")
    return {"plan": {"version": 1, "audio": plan["audio"],
                      "duration_seconds": scene["end"],
                      "style": plan.get("style", "mythological_3d"),
                      "scenes": [{**scene, "start": 0}]},
            "urls": {"1": image_url}}

def save(path, data):
    with path.open("x", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=2)
        out.write("\n")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--image-url", required=True)
    p.add_argument("--plan-output", type=Path, required=True)
    p.add_argument("--urls-output", type=Path, required=True)
    p.add_argument("--audio-output", type=Path, required=True, help="trimmed one-scene narration")
    args=p.parse_args()
    try:
        if args.pilot.stat().st_size > 4*1024*1024:
            raise ValueError("pilot input too large")
        value=build(json.loads(args.pilot.read_text(encoding="utf-8")),args.image_url)
        destinations = [args.plan_output, args.urls_output, args.audio_output]
        if len(set(map(str,destinations))) != 3 or any(x.exists() or x.is_symlink() for x in destinations):
            raise ValueError("output already exists or paths overlap")
        original = Path(value["plan"]["audio"])
        if not original.is_file() or original.is_symlink():
            raise ValueError("pilot narration file missing or symlinked")
        length = value["plan"]["duration_seconds"]
        if not args.audio_output.parent.is_dir():
            raise ValueError("audio output directory must exist")
        with tempfile.TemporaryDirectory(prefix=".provider-audio-", dir=args.audio_output.parent) as temp:
            staged = Path(temp) / "scene.m4a"
            subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-y", "-i", str(original),
                            "-t", f"{length:.6f}", "-vn", "-c:a", "aac", str(staged)], check=True)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "default=noprint_wrappers=1:nokey=1", str(staged)],
                                   capture_output=True, text=True, check=True)
            measured = float(probe.stdout.strip())
            if not math.isfinite(measured) or abs(measured - length) > 0.15:
                raise ValueError("trimmed narration does not match scene duration")
            value["plan"]["audio"] = str(args.audio_output)
            os.link(staged, args.audio_output)
            try:
                save(args.plan_output, value["plan"])
                try:
                    save(args.urls_output, value["urls"])
                except Exception:
                    args.plan_output.unlink(missing_ok=True)
                    raise
            except Exception:
                args.audio_output.unlink(missing_ok=True)
                raise
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        p.exit(1,f"Provider pilot preparation failed: {exc}\n")
    print("One-scene pilot audio and request prepared; no paid API calls made.")

if __name__=="__main__": main()

#!/usr/bin/env python3
"""Prepare a one-scene Runway pilot request. Never submits API requests."""
import argparse
import json
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
    args=p.parse_args()
    try:
        if args.pilot.stat().st_size > 4*1024*1024:
            raise ValueError("pilot input too large")
        value=build(json.loads(args.pilot.read_text(encoding="utf-8")),args.image_url)
        if args.plan_output.exists() or args.urls_output.exists() or args.plan_output==args.urls_output:
            raise ValueError("output already exists or paths overlap")
        # Keep preview-only manifests; no provider invocation.
        save(args.plan_output,value["plan"])
        try: save(args.urls_output,value["urls"])
        except Exception:
            args.plan_output.unlink(missing_ok=True)
            raise
    except (ValueError, OSError, KeyError, TypeError) as exc:
        p.exit(1,f"Provider pilot preparation failed: {exc}\n")
    print("One-scene pilot request prepared; no paid API calls made.")

if __name__=="__main__": main()

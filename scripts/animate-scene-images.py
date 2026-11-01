#!/usr/bin/env python3
"""Create real image-to-video animation tasks with Runway (opt-in).

Provide a JSON mapping of scene IDs to publicly accessible HTTPS image URLs.
Preview by default. --execute explicitly submits paid tasks; task ids are saved.
"""
import argparse
import json
import os
import urllib.parse
from pathlib import Path

def build_jobs(plan, urls, limit):
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1..100")
    if plan.get("version") != 1 or not isinstance(plan.get("scenes"), list):
        raise ValueError("invalid Phase 9 scene plan")
    jobs = []
    for scene in plan["scenes"][:limit]:
        index = scene["index"]
        image = urls.get(str(index))
        if not isinstance(image, str):
            raise ValueError(f"missing public image URL for scene {index}")
        parsed = urllib.parse.urlparse(image)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError(f"scene {index} requires HTTPS image URL")
        prompt = scene.get("visual_prompt", "")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
            raise ValueError(f"invalid visual prompt for scene {index}")
        jobs.append({"scene": index, "start": scene["start"], "end": scene["end"],
                     "image": image, "prompt": prompt.strip(),
                     "duration": 5})
    if not jobs:
        raise ValueError("no scenes")
    return jobs

def submit(jobs, client):
    result = []
    for job in jobs:
        task = client.image_to_video.create(model="gen4_turbo", prompt_image=job["image"],
                                            prompt_text=job["prompt"], ratio="1280:720",
                                            duration=job["duration"])
        result.append({"scene": job["scene"], "task_id": task.id,
                       "status": "submitted", "duration": job["duration"]})
    return result

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--image-urls", type=Path, required=True,
                   help='JSON object mapping scene indexes to HTTPS image URLs')
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, default=1)
    p.add_argument("--execute", action="store_true", help="submit paid Runway tasks")
    args = p.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite output")
        if args.plan.stat().st_size > 4*1024*1024 or args.image_urls.stat().st_size > 128*1024:
            raise ValueError("input JSON too large")
        jobs = build_jobs(json.loads(args.plan.read_text()), json.loads(args.image_urls.read_text()), args.limit)
        if args.execute:
            if not os.environ.get("RUNWAYML_API_SECRET"):
                raise ValueError("RUNWAYML_API_SECRET required for --execute")
            try:
                from runwayml import RunwayML
            except ImportError as exc:
                raise ValueError("install runwayml with pip to execute") from exc
            result = submit(jobs, RunwayML())
        else:
            result = jobs
        with args.output.open("x", encoding="utf-8") as file:
            json.dump({"mode": "submitted" if args.execute else "preview",
                       "clips": result}, file, indent=2, ensure_ascii=False)
            file.write("\n")
        print(f"Saved {len(result)} scene animation entries to {args.output}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        p.exit(1, f"Animation planning failed: {exc}\n")

if __name__ == "__main__":
    main()

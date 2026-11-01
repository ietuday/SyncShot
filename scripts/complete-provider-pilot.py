#!/usr/bin/env python3
"""Complete an existing one-scene Runway task: inspect, optional download, validate, assemble.

Never submits AI generation jobs. Downloads are explicitly opted in with --download.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path

def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

retrieve = load("retrieve-animation-clips.py", "retrieve_animation")
demo = load("build-provider-demo.py", "build_animation_demo")

def finish(tasks, plan, client, clips_dir, output, report, download=False,
           collector=retrieve.collect, builder=demo.build_demo):
    entries = tasks.get("clips")
    if tasks.get("mode") != "submitted" or not isinstance(entries, list) or len(entries) != 1:
        raise ValueError("expected exactly one previously submitted generation task")
    if entries[0].get("scene") != 1:
        raise ValueError("only scene 1 may be completed")
    if not isinstance(plan.get("scenes"), list) or len(plan["scenes"]) != 1:
        raise ValueError("expected one-scene plan")
    if output.exists() or report.exists() or output.is_symlink() or report.is_symlink():
        raise FileExistsError("demo output/report already exists")
    existing_clip = clips_dir / "scene-0001.mp4"
    # A previous invocation may have downloaded the clip before assembly failed.
    # Never overwrite a recovered clip; recheck provider status and reuse it.
    should_download = download and not (existing_clip.exists() or existing_clip.is_symlink())
    if should_download:
        result = collector(tasks, client, clips_dir, True)
        if len(result["clips"]) != 1 or result["clips"][0]["status"] != "SUCCEEDED":
            raise ValueError("provider task has not succeeded")
    else:
        result = collector(tasks, client, clips_dir, False)
        if len(result["clips"]) != 1 or result["clips"][0]["status"] != "SUCCEEDED":
            raise ValueError("provider task has not succeeded")
        if not existing_clip.is_file() or existing_clip.is_symlink():
            raise ValueError("clip absent; explicitly use --download or supply a downloaded clip")
    return builder(plan, clips_dir, output, report)

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tasks", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--clips-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--download", action="store_true", help="download existing completed clip")
    args = p.parse_args(argv)
    try:
        if args.tasks.stat().st_size > 128*1024 or args.plan.stat().st_size > 4*1024*1024:
            raise ValueError("input too large")
        if not os.environ.get("RUNWAYML_API_SECRET"):
            raise ValueError("RUNWAYML_API_SECRET required to check existing task")
        from runwayml import RunwayML
        outcome = finish(json.loads(args.tasks.read_text(encoding="utf-8")),
                         json.loads(args.plan.read_text(encoding="utf-8")), RunwayML(),
                         args.clips_dir, args.output, args.report, args.download)
    except (OSError, ValueError, ImportError, KeyError) as exc:
        p.exit(1, f"Provider pilot completion failed: {exc}\n")
    print(f"Verified animation demo: {outcome['video_output']}")

if __name__ == "__main__":
    main()

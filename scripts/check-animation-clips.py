#!/usr/bin/env python3
"""Validate that every planned animation clip exists and is decodable by ffprobe."""
import argparse
import json
import math
import subprocess
from pathlib import Path

def check(plan, directory, probe):
    scenes = plan.get("scenes")
    if plan.get("version") != 1 or not isinstance(scenes, list) or not 1 <= len(scenes) <= 1000:
        raise ValueError("expected a version 1 scene plan with 1..1000 scenes")
    results = []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict) or scene.get("index") != index:
            raise ValueError(f"invalid scene index {index}")
        path = directory / f"scene-{index:04d}.mp4"
        item = {"scene": index, "path": str(path)}
        if path.is_symlink() or not path.is_file():
            item.update(status="missing", action="download or regenerate this scene")
        elif path.stat().st_size == 0:
            item.update(status="invalid", action="remove corrupt file then download again", reason="empty file")
        else:
            try:
                data = probe(path)
                streams = data.get("streams", [])
                videos = [s for s in streams if s.get("codec_type") == "video"]
                duration = float(data.get("format", {}).get("duration", "nan"))
                if not videos or not math.isfinite(duration) or duration <= 0:
                    raise ValueError("no valid video stream or duration")
                item.update(status="ready", duration_seconds=duration)
            except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                item.update(status="invalid", action="remove corrupt file then download again",
                            reason=str(exc)[:300])
        results.append(item)
    counts = {status: sum(x["status"] == status for x in results)
              for status in ("ready", "missing", "invalid")}
    return {"complete": counts["ready"] == len(results), "counts": counts, "scenes": results}

def ffprobe(path):
    cp = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                         "format=duration:stream=codec_type", "-of", "json", str(path)],
                        text=True, capture_output=True, check=True, timeout=30)
    return json.loads(cp.stdout)

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--clips-dir", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if args.report.exists() or args.report.is_symlink():
            raise ValueError("refusing to overwrite report")
        if args.plan.stat().st_size > 4*1024*1024:
            raise ValueError("scene plan exceeds size limit")
        result = check(json.loads(args.plan.read_text(encoding="utf-8")), args.clips_dir, ffprobe)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
        print(f"Clip readiness: {result['counts']}; complete={result['complete']}")
        return 0 if result["complete"] else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        p.exit(1, f"Clip readiness failed: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())

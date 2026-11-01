#!/usr/bin/env python3
"""Prepare a short, bounded animation pilot from an existing Phase 9 scene plan.

No paid API calls, uploads, downloads, or FFmpeg rendering.
"""
import argparse
import json
import math
from pathlib import Path


def prepare(plan, limit_seconds=30, max_scenes=5):
    if not math.isfinite(limit_seconds) or not 1 <= limit_seconds <= 120:
        raise ValueError("pilot seconds must be 1..120")
    if not 1 <= max_scenes <= 20:
        raise ValueError("max scenes must be 1..20")
    if plan.get("version") != 1 or not isinstance(plan.get("scenes"), list):
        raise ValueError("expected Phase 9 scene plan")
    audio = plan.get("audio")
    if not isinstance(audio, str) or not audio.strip():
        raise ValueError("source audio required")
    scenes = []
    expected_start = 0.0
    for scene in plan["scenes"]:
        if len(scenes) >= max_scenes or expected_start >= limit_seconds - 0.001:
            break
        if not isinstance(scene, dict):
            raise ValueError("invalid scene")
        start, end = scene.get("start"), scene.get("end")
        prompt = scene.get("visual_prompt")
        if (not isinstance(start, (int, float)) or not isinstance(end, (int, float))
                or not math.isfinite(start) or not math.isfinite(end)
                or abs(start - expected_start) > 0.02 or end <= start
                or not isinstance(prompt, str) or not prompt.strip()):
            raise ValueError("scene timeline must be contiguous and have prompts")
        clipped_end = min(end, limit_seconds)
        scenes.append({**scene, "index": len(scenes) + 1,
                       "start": start, "end": clipped_end})
        expected_start = clipped_end
    if not scenes:
        raise ValueError("no scenes available for pilot")
    return {"version": 1, "audio": audio, "duration_seconds": scenes[-1]["end"],
            "style": plan.get("style", "mythological_3d"), "scenes": scenes,
            "pilot": {"source": "scene-plan", "limited_to_seconds": limit_seconds,
                      "max_scenes": max_scenes,
                      "audio_requires_trim": True}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--max-scenes", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite pilot plan")
        if args.plan.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("input plan exceeds 4 MiB")
        result = prepare(json.loads(args.plan.read_text(encoding="utf-8")),
                         args.seconds, args.max_scenes)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"Animation pilot preparation failed: {exc}\n")
    print(f"Prepared {len(result['scenes'])} pilot scenes covering {result['duration_seconds']:.2f} seconds")
    print("NOTE: Trim narration to this duration before final assembly; this tool does not trim audio.")


if __name__ == "__main__":
    main()

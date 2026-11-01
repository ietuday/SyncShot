#!/usr/bin/env python3
"""Inspect decoded Shorts frames for blank or near-black visual content."""
import argparse
import json
import math
import subprocess
from pathlib import Path

def sample_frame(path, at_seconds):
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
         "-ss", str(at_seconds), "-i", str(path), "-frames:v", "1",
         "-vf", "scale=64:64", "-pix_fmt", "gray", "-f", "rawvideo", "-"],
        check=True, capture_output=True)
    if len(result.stdout) != 64 * 64:
        raise ValueError(f"{path}: failed to decode a complete sampled frame")
    pixels = result.stdout
    mean = sum(pixels) / len(pixels)
    variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    return {"timestamp_seconds": at_seconds, "mean_luma": round(mean, 2),
            "luma_stddev": round(math.sqrt(variance), 2)}

def inspect(folder, minimum_luma=12, minimum_stddev=5):
    shorts = sorted(Path(folder).glob("*.mp4"))
    if not shorts:
        raise ValueError("no Shorts found")
    output = []
    for clip in shorts:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
            capture_output=True, check=True, text=True)
        duration = float(probe.stdout.strip())
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError(f"{clip.name}: invalid duration")
        frames = [sample_frame(clip, duration * fraction) for fraction in (0.25, 0.5, 0.75)]
        if any(frame["mean_luma"] < minimum_luma or frame["luma_stddev"] < minimum_stddev
               for frame in frames):
            raise ValueError(f"{clip.name}: blank/dark/flat sampled frame")
        output.append({"clip": clip.name, "samples": frames})
    return {"clip_count": len(output), "clips": output}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("shorts_dir")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    payload = json.dumps(inspect(args.shorts_dir), indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()

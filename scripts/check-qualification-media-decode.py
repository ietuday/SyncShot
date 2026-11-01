#!/usr/bin/env python3
"""Decode selected media inputs before starting a costly production render."""
import argparse
import json
import subprocess
from pathlib import Path

AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp"}

def discover(paths):
    found = set()
    for raw in paths:
        path = Path(raw).resolve()
        if not path.exists():
            raise ValueError(f"missing media input: {raw}")
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            found.update(p.resolve() for p in path.rglob("*") if p.is_file())
        else:
            raise ValueError(f"unsupported input: {raw}")
    return sorted(p for p in found if p.suffix.lower() in AUDIO | IMAGE)

def check_media(paths, timeout=120):
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    checked = []
    for path in discover(paths):
        kind = "audio" if path.suffix.lower() in AUDIO else "image"
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "json", str(path)],
            text=True, capture_output=True, check=True, timeout=timeout)
        streams = json.loads(probe.stdout).get("streams", [])
        if not any(s.get("codec_type") == kind or
                   (kind == "image" and s.get("codec_type") == "video") for s in streams):
            raise ValueError(f"{path}: missing decodable {kind} stream")
        # FFprobe alone cannot detect corruption in encoded packets. Decode the
        # complete selected stream; reject any decoder errors and timeouts.
        selector = "0:a:0" if kind == "audio" else "0:v:0"
        try:
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-xerror",
                 "-i", str(path), "-map", selector, "-f", "null", "-"],
                capture_output=True, check=True, timeout=timeout)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise ValueError(f"{path}: {kind} decode failed") from exc
        checked.append({"name": path.name, "type": kind, "bytes": path.stat().st_size})
    if not checked:
        raise ValueError("no recognized media files to decode")
    if not any(x["type"] == "audio" for x in checked) or not any(x["type"] == "image" for x in checked):
        raise ValueError("both audio and images must be decoded")
    return {"checked_count": len(checked), "files": checked}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+")
    p.add_argument("--timeout-per-file", type=float, default=120)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    payload = json.dumps(check_media(args.inputs, args.timeout_per_file), indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()

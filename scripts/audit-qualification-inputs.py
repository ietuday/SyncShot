#!/usr/bin/env python3
"""Audit media input paths listed for production qualification."""
import argparse
import json
from pathlib import Path

MEDIA_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".png", ".jpg", ".jpeg", ".webp"}

def audit(paths):
    files = set()
    for raw in paths:
        path = Path(raw).resolve()
        if not path.exists():
            raise ValueError(f"missing input: {raw}")
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = (p for p in path.rglob("*") if p.is_file())
        else:
            raise ValueError(f"unsupported input path: {raw}")
        files.update(p.resolve() for p in candidates)
    media = sorted(p for p in files if p.suffix.lower() in MEDIA_EXT)
    if not media:
        raise ValueError("no recognized audio or image media inputs")
    empty = [str(p) for p in media if p.stat().st_size == 0]
    if empty:
        raise ValueError("empty media files: " + ", ".join(empty[:10]))
    audio = sum(p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"} for p in media)
    images = len(media) - audio
    if not audio or not images:
        raise ValueError("both audio and image media are required for qualification")
    return {"audio_file_count": audio, "image_file_count": images,
            "total_media_bytes": sum(p.stat().st_size for p in media)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    payload = json.dumps(audit(a.paths), indent=2) + "\n"
    if a.output:
        a.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()

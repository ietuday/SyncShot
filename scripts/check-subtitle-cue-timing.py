#!/usr/bin/env python3
"""Check authored SRT cue timing against rendered media, without OCR claims."""
import argparse
import json
import re
import subprocess
from pathlib import Path

TIMING = re.compile(r"^(\d{2,}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2,}):(\d{2}):(\d{2}),(\d{3})(?: .*)?$")

def seconds(values):
    hh, mm, ss, ms = map(int, values)
    if mm >= 60 or ss >= 60:
        raise ValueError("invalid SRT timestamp")
    return hh * 3600 + mm * 60 + ss + ms / 1000

def inspect(srt, video):
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
                           capture_output=True, text=True, check=True)
    duration = float(probe.stdout.strip())
    if not 0 < duration < float("inf"):
        raise ValueError("invalid video duration")
    blocks = re.split(r"\n\s*\n", Path(srt).read_text(encoding="utf-8-sig").strip().replace("\r\n", "\n"))
    cues = []
    previous_end = 0
    for i, block in enumerate(blocks, start=1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0].strip() != str(i) or not "".join(lines[2:]).strip():
            raise ValueError(f"invalid SRT cue {i}")
        match = TIMING.fullmatch(lines[1].strip())
        if not match:
            raise ValueError(f"invalid SRT timing in cue {i}")
        start = seconds(match.groups()[:4])
        end = seconds(match.groups()[4:])
        if start < previous_end or end <= start or end > duration + 0.1:
            raise ValueError(f"cue {i} outside media duration or overlapping")
        cues.append({"index": i, "start_seconds": start, "end_seconds": end,
                     "midpoint_seconds": (start + end) / 2})
        previous_end = end
    return {"video_duration_seconds": duration, "cue_count": len(cues), "cues": cues}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("srt")
    parser.add_argument("video")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(inspect(args.srt, args.video), indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()

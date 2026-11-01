#!/usr/bin/env python3
"""Validate all produced Shorts using encoded stream metadata and audio decoding."""
import argparse
import json
import math
from pathlib import Path
import subprocess

def inspect(folder, maximum):
    clips = sorted(Path(folder).glob("*.mp4"))
    if not clips:
        raise ValueError("no Shorts MP4 files produced")
    results = []
    for clip in clips:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", str(clip)], capture_output=True, text=True, check=True)
        data = json.loads(probe.stdout)
        videos = [s for s in data["streams"] if s.get("codec_type") == "video"]
        audios = [s for s in data["streams"] if s.get("codec_type") == "audio"]
        duration = float(data["format"]["duration"])
        if len(videos) != 1 or not audios:
            raise ValueError(f"{clip.name}: missing video/audio stream")
        if (videos[0].get("width"), videos[0].get("height")) != (1080, 1920):
            raise ValueError(f"{clip.name}: expected 1080x1920 portrait")
        if videos[0].get("codec_name") != "h264" or audios[0].get("codec_name") != "aac":
            raise ValueError(f"{clip.name}: expected H.264/AAC")
        if not 0 < duration <= maximum + 0.5:
            raise ValueError(f"{clip.name}: invalid duration {duration}")
        # Container duration alone can hide gaps or delayed audio streams.
        timings = []
        for kind, stream in (("video", videos[0]), ("audio", audios[0])):
            try:
                start = float(stream.get("start_time", "0"))
                length = float(stream["duration"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"{clip.name}: missing {kind} timing") from exc
            if not all(map(math.isfinite, (start, length))) or length <= 0:
                raise ValueError(f"{clip.name}: invalid {kind} timing")
            timings.append((start, start + length))
        start_delta = abs(timings[0][0] - timings[1][0])
        end_delta = abs(timings[0][1] - timings[1][1])
        if start_delta > 0.25 or end_delta > 0.5:
            raise ValueError(f"{clip.name}: audio/video stream boundaries misaligned: "
                             f"start {start_delta:.3f}s, end {end_delta:.3f}s")
        # A complete audio decode detects truncation and corrupted packets.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                        "-i", str(clip), "-map", "0:a:0", "-vn", "-f", "null", "-"],
                       capture_output=True, check=True)
        results.append({"name": clip.name, "duration_seconds": duration,
                        "width": 1080, "height": 1920, "audio_decodable": True,
                        "av_start_delta_seconds": round(start_delta, 3),
                        "av_end_delta_seconds": round(end_delta, 3)})
    return {"clip_count": len(results), "clips": results}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("shorts_dir")
    p.add_argument("--max-duration", type=float, default=60)
    p.add_argument("--evidence", type=Path)
    a = p.parse_args()
    payload = json.dumps(inspect(a.shorts_dir, a.max_duration), indent=2) + "\n"
    if a.evidence:
        a.evidence.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")

if __name__ == "__main__":
    main()

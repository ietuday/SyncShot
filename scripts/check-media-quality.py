#!/usr/bin/env python3
"""Validate actual encoded video dimensions, audio and duration with ffprobe."""
import argparse
import json
import math
import subprocess

def inspect(path, width, height, minimum, maximum):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(path)], capture_output=True, text=True, check=True
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    if len(videos) != 1 or len(audios) < 1:
        raise ValueError("expected exactly one video and at least one audio stream")
    video = videos[0]
    if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
        raise ValueError("unexpected video dimensions")
    if video.get("codec_name") != "h264":
        raise ValueError("expected H.264 video")
    if audios[0].get("codec_name") != "aac":
        raise ValueError("expected AAC audio")
    duration = float(payload["format"]["duration"])
    if not math.isfinite(duration) or not minimum <= duration <= maximum:
        raise ValueError("unexpected or invalid media duration")
    for stream in (video, audios[0]):
        if stream.get("duration") not in (None, "N/A"):
            stream_duration = float(stream["duration"])
            if not math.isfinite(stream_duration) or abs(stream_duration - duration) > 1.5:
                raise ValueError("stream duration substantially differs from container duration")
    return {"video_codec": video["codec_name"], "audio_codec": audios[0]["codec_name"],
            "width": width, "height": height, "duration_seconds": duration}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--min-duration", type=float, default=1)
    parser.add_argument("--max-duration", type=float, default=5)
    args = parser.parse_args()
    print(json.dumps(inspect(args.video, args.width, args.height,
                             args.min_duration, args.max_duration), indent=2))

if __name__ == "__main__":
    main()

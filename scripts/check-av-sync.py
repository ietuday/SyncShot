#!/usr/bin/env python3
"""Compare container audio/video endpoints (not perceptual sync)."""
import argparse
import json
import subprocess

def validate(media: str, max_drift: float) -> None:
    data = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration",
         "-of", "json", media], text=True)
    streams = json.loads(data)["streams"]
    def bounds(kind):
        for stream in streams:
            if stream.get("codec_type") == kind and stream.get("duration") is not None:
                start = float(stream.get("start_time", "0"))
                return start, start + float(stream["duration"])
        raise ValueError(f"missing {kind} stream or stream duration")
    v_start, v_end = bounds("video")
    a_start, a_end = bounds("audio")
    if abs(v_start-a_start)>max_drift or abs(v_end-a_end)>max_drift:
        raise ValueError(f"audio/video endpoint drift: start={abs(v_start-a_start):.3f}s end={abs(v_end-a_end):.3f}s")
    print(f"AV endpoints within {max_drift:.3f}s: start drift {abs(v_start-a_start):.3f}s, end drift {abs(v_end-a_end):.3f}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("media")
    parser.add_argument("--max-drift-seconds", type=float, default=0.5)
    args=parser.parse_args()
    if args.max_drift_seconds<0:
        parser.error("max drift must be >=0")
    try:
        validate(args.media,args.max_drift_seconds)
    except (ValueError, subprocess.CalledProcessError, KeyError) as exc:
        parser.exit(1,f"Audio/video alignment failed: {exc}\n")

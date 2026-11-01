#!/usr/bin/env python3
"""Read-only preflight for original narration and images before long qualification."""
import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

AUDIO={".mp3",".m4a",".wav",".aac",".flac",".ogg"}
IMAGES={".jpg",".jpeg",".png",".webp"}
def probe(path):
    cmd=["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(path)]
    result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if result.returncode:
        raise ValueError(f"ffprobe cannot read {path.name}: {result.stderr.strip()[:160]}")
    try:
        duration=float(result.stdout.strip())
    except ValueError:
        raise ValueError(f"invalid duration for {path.name}") from None
    if not math.isfinite(duration) or duration<=0:
        raise ValueError(f"nonpositive duration for {path.name}")
    stream=subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
                           "-show_entries","stream=codec_type",
                           "-of","default=noprint_wrappers=1:nokey=1",str(path)],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if stream.returncode or stream.stdout.strip()!="audio":
        raise ValueError(f"no readable audio stream in {path.name}")
    return duration

def preflight(audio_dir, image_dir, report_dir, minimum_free_gib):
    audio=[p for p in audio_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO]
    images=[p for p in image_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGES]
    if not audio: raise ValueError("no supported narration files found")
    if not images: raise ValueError("no supported images found")
    durations={p.name:round(probe(p),2) for p in audio}
    for image in images:
        command=["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height",
                 "-of","csv=p=0",str(image)]
        r=subprocess.run(command,capture_output=True,text=True)
        parts=r.stdout.strip().split(",")
        if r.returncode or len(parts)!=2 or not all(v.isdigit() and int(v)>0 for v in parts):
            raise ValueError(f"invalid image: {image.name}")
    if not math.isfinite(minimum_free_gib) or minimum_free_gib < 0:
        raise ValueError("minimum free disk must be finite and nonnegative")
    free=shutil.disk_usage(report_dir).free/1024**3
    if free<minimum_free_gib:
        raise ValueError(f"insufficient free disk: {free:.2f} GiB; need {minimum_free_gib:.2f} GiB")
    return {"audio_files":len(audio),"image_files":len(images),
            "audio_durations_seconds":durations,"free_disk_gib":round(free,2)}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("audio_dir",type=Path)
    parser.add_argument("image_dir",type=Path)
    parser.add_argument("report_dir",type=Path)
    parser.add_argument("--minimum-free-gib",type=float,default=2.0)
    args=parser.parse_args()
    try: print(json.dumps(preflight(args.audio_dir,args.image_dir,args.report_dir,args.minimum_free_gib),indent=2))
    except (OSError,ValueError) as exc: parser.exit(2,f"Real-media preflight failed: {exc}\n")

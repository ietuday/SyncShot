#!/usr/bin/env python3
"""Verify one downloaded provider clip against the intended scene, without paid API calls."""
import argparse
import json
import math
import subprocess
from pathlib import Path

def verify(plan, clip, probe):
    scenes=plan.get("scenes")
    if plan.get("version")!=1 or not isinstance(scenes,list) or len(scenes)!=1:
        raise ValueError("expected a one-scene plan")
    scene=scenes[0]
    if scene.get("index")!=1 or scene.get("start")!=0:
        raise ValueError("scene must start at zero and have index 1")
    target=scene.get("end")
    if not isinstance(target,(int,float)) or isinstance(target,bool) or not math.isfinite(target) or not 0<target<=120:
        raise ValueError("invalid scene target duration")
    if not clip.is_file() or clip.is_symlink():
        raise ValueError("downloaded provider clip missing or is a symlink")
    data=probe(clip)
    video=[s for s in data.get("streams",[]) if s.get("codec_type")=="video"]
    duration=float(data.get("format",{}).get("duration","nan"))
    if not video or not math.isfinite(duration) or duration<=0:
        raise ValueError("provider clip lacks valid video stream or duration")
    return {"ready":True,"clip":str(clip),"source_duration_seconds":duration,
            "scene_duration_seconds":target,
            "will_loop":duration<target-0.02,
            "will_trim":duration>target+0.02,
            "note":"Visual quality, lip sync and provider authenticity are not automatically verified."}

def ffprobe(path):
    out=subprocess.run(["ffprobe","-v","error","-show_entries",
        "format=duration:stream=codec_type","-of","json",str(path)],
        text=True,capture_output=True,check=True,timeout=30)
    return json.loads(out.stdout)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",type=Path,required=True)
    parser.add_argument("--clip",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.report.exists() or args.report.is_symlink():
            raise ValueError("report already exists")
        if args.plan.stat().st_size>4*1024*1024:
            raise ValueError("plan exceeds 4 MiB")
        result=verify(json.loads(args.plan.read_text(encoding="utf-8")),args.clip,ffprobe)
        with args.report.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2)
            f.write("\n")
    except (OSError,ValueError,TypeError,subprocess.CalledProcessError) as error:
        parser.exit(1,f"Provider clip verification failed: {error}\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()

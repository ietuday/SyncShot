#!/usr/bin/env python3
"""Trim a pilot plan's audio and emit a matching plan, without touching originals."""
import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path


def duration_of(path, runner=subprocess.run):
    cp=runner(["ffprobe","-v","error","-show_entries","format=duration",
               "-of","default=noprint_wrappers=1:nokey=1",str(path)],
              capture_output=True,text=True,check=True)
    seconds=float(cp.stdout.strip())
    if not math.isfinite(seconds) or seconds<=0:
        raise ValueError("invalid audio duration")
    return seconds


def prepare(plan, out_audio, out_plan, runner=subprocess.run, probe=duration_of):
    if plan.get("version")!=1:
        raise ValueError("expected Phase 9 plan version 1")
    target=plan.get("duration_seconds")
    if not isinstance(target,(float,int)) or isinstance(target,bool) or not math.isfinite(target) or not 0<target<=120:
        raise ValueError("pilot duration must be 0..120 seconds")
    audio=Path(plan.get("audio",""))
    if not audio.is_file() or audio.is_symlink():
        raise ValueError("narration audio must be a regular file")
    if out_audio.exists() or out_audio.is_symlink() or out_plan.exists() or out_plan.is_symlink():
        raise FileExistsError("refusing to overwrite pilot outputs")
    if not out_audio.parent.is_dir() or not out_plan.parent.is_dir():
        raise ValueError("output parent directory must exist")
    if probe(audio)+0.1 < target:
        raise ValueError("source audio shorter than pilot duration")
    with tempfile.TemporaryDirectory(prefix=".pilot-audio-",dir=out_audio.parent) as tmp:
        temporary=Path(tmp)/"audio.m4a"
        runner(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                "-i",str(audio),"-t",f"{target:.6f}","-vn","-c:a","aac",
                "-b:a","160k",str(temporary)],check=True)
        actual=probe(temporary)
        if abs(actual-target)>0.15:
            raise ValueError(f"pilot audio duration mismatch: expected {target:.3f}, got {actual:.3f}")
        updated=dict(plan)
        updated["audio"]=str(out_audio)
        updated["duration_seconds"]=target
        updated["pilot_audio_measured_seconds"]=actual
        updated["pilot_audio_prepared"]=True
        # Exclusive links publish complete outputs; if publishing the manifest fails,
        # remove only the audio created by this process.
        os.link(temporary,out_audio)
        try:
            with out_plan.open("x",encoding="utf-8") as file:
                json.dump(updated,file,ensure_ascii=False,indent=2)
                file.write("\n")
        except Exception:
            out_audio.unlink()
            raise
    return updated


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--audio-output",type=Path,required=True)
    p.add_argument("--plan-output",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.plan.stat().st_size>4*1024*1024:
            raise ValueError("pilot plan exceeds 4 MiB")
        data=json.loads(args.plan.read_text(encoding="utf-8"))
        result=prepare(data,args.audio_output,args.plan_output)
    except (OSError,ValueError,TypeError,subprocess.CalledProcessError) as exc:
        p.exit(1,f"Pilot audio preparation failed: {exc}\n")
    print(f"Prepared pilot narration ({result['duration_seconds']:.3f}s): {args.audio_output}")


if __name__=="__main__":
    main()

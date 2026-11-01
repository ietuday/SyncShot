#!/usr/bin/env python3
"""Guide a ready pilot through zero-charge preview of image/animation requests.

Does not submit AI jobs or invoke --execute. Requires a prepared pilot-ready JSON.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

def commands(plan, urls, limit, root, workdir):
    data=json.loads(plan.read_text(encoding="utf-8"))
    scenes=data.get("scenes")
    if data.get("version")!=1 or not data.get("pilot_audio_prepared") or not isinstance(scenes,list) or not scenes:
        raise ValueError("requires Phase 9.12 pilot-ready JSON")
    if not 1<=limit<=min(20,len(scenes)):
        raise ValueError("limit exceeds pilot scene count")
    image=[sys.executable,str(root/"scripts/generate-scene-images.py"),"--plan",str(plan),
           "--output-dir",str(workdir/"images"),"--limit",str(limit)]
    animation=None
    if urls is not None:
        animation=[sys.executable,str(root/"scripts/animate-scene-images.py"),
                   "--plan",str(plan),"--image-urls",str(urls),"--output",
                   str(workdir/"animation-preview.json"),"--limit",str(limit)]
    return [image]+([animation] if animation else [])

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pilot",type=Path,required=True)
    p.add_argument("--workdir",type=Path,required=True)
    p.add_argument("--image-urls",type=Path)
    p.add_argument("--limit",type=int,default=3)
    args=p.parse_args(argv)
    try:
        root=Path(__file__).resolve().parent.parent
        if args.pilot.stat().st_size>4*1024*1024:
            raise ValueError("pilot plan too large")
        if not args.workdir.is_dir():
            raise ValueError("workdir must already exist")
        for cmd in commands(args.pilot,args.image_urls,args.limit,root,args.workdir):
            subprocess.run(cmd,cwd=root,check=True)
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        p.exit(1,f"Pilot preview failed: {e}\n")
    print("Preview complete; no paid AI generation was requested.")

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Offline readiness gate for a single-scene paid-provider pilot. No network calls."""
import argparse
import json
import math
from pathlib import Path
from urllib.parse import urlsplit

def inspect(plan, urls):
    issues=[]
    scenes=plan.get("scenes") if isinstance(plan,dict) else None
    if not isinstance(scenes,list) or len(scenes)!=1:
        issues.append("exactly one scene required")
    else:
        s=scenes[0]
        if not isinstance(s,dict) or s.get("index")!=1:
            issues.append("scene index must be 1")
        start,end=s.get("start"),s.get("end")
        if not isinstance(start,(float,int)) or isinstance(start,bool) or start!=0:
            issues.append("scene must start at zero")
        if not isinstance(end,(float,int)) or isinstance(end,bool) or not math.isfinite(end) or end<=0 or end>5:
            issues.append("pilot scene duration must be between 0 and 5 seconds")
        if not isinstance(s.get("visual_prompt"),str) or not s["visual_prompt"].strip():
            issues.append("visual prompt required")
        if isinstance(end,(float,int)) and isinstance(plan.get("duration_seconds"),(float,int)) and abs(end-plan["duration_seconds"])>0.01:
            issues.append("scene and plan duration mismatch")
    audio=plan.get("audio") if isinstance(plan,dict) else None
    if not isinstance(audio,str) or not Path(audio).is_file():
        issues.append("prepared narration audio missing")
    url=urls.get("1") if isinstance(urls,dict) else None
    if not isinstance(url,str):
        issues.append("HTTPS hosted illustration required")
    else:
        parsed=urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
            issues.append("illustration must use HTTPS without credentials")
    return {"ready":not issues,"issues":issues,"scene_count":len(scenes) if isinstance(scenes,list) else 0,
            "provider_requests_submitted":0}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--image-urls",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.report.exists() or args.report.is_symlink():
            raise ValueError("report exists")
        if args.plan.stat().st_size>4*1024*1024 or args.image_urls.stat().st_size>128*1024:
            raise ValueError("input too large")
        result=inspect(json.loads(args.plan.read_text()),json.loads(args.image_urls.read_text()))
        with args.report.open("x",encoding="utf-8") as output:
            json.dump(result,output,indent=2)
            output.write("\n")
    except (OSError,ValueError,TypeError) as exc:
        p.exit(1,f"Provider pilot readiness failed: {exc}\n")
    print(json.dumps(result,indent=2))
    return 0 if result["ready"] else 2

if __name__=="__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build a deterministic summary of qualification preflight results."""
import argparse
import json
from pathlib import Path

def summarize(audit, decoded, fingerprint):
    a=json.loads(Path(audit).read_text(encoding="utf-8"))
    d=json.loads(Path(decoded).read_text(encoding="utf-8"))
    f=json.loads(Path(fingerprint).read_text(encoding="utf-8"))
    total=a["audio_file_count"]+a["image_file_count"]
    if d["checked_count"]!=total:
        raise ValueError("media audit and decoder count mismatch")
    if not f.get("fingerprint"):
        raise ValueError("missing input fingerprint")
    return {"input_fingerprint":f["fingerprint"],
            "audio_file_count":a["audio_file_count"],
            "image_file_count":a["image_file_count"],
            "decoded_file_count":d["checked_count"],
            "total_media_bytes":a["total_media_bytes"]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("audit")
    p.add_argument("decoded")
    p.add_argument("fingerprint")
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=summarize(args.audit,args.decoded,args.fingerprint)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()

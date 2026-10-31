#!/usr/bin/env python3
"""Fingerprint benchmark input files without recording private file contents."""
import argparse
import hashlib
import json
from pathlib import Path

def fingerprint(paths):
    entries = []
    for source_index, raw in enumerate(paths):
        path = Path(raw)
        if not path.exists():
            raise FileNotFoundError(str(path))
        files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
        for file in files:
            digest = hashlib.sha256()
            with file.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            entries.append({"source_index": source_index, "file": str(file.relative_to(path) if path.is_dir() else path.name),
                            "bytes": file.stat().st_size, "sha256": digest.hexdigest()})
    combined = hashlib.sha256(json.dumps(entries, sort_keys=True).encode("utf-8")).hexdigest()
    return {"fingerprint": combined, "files": len(entries), "bytes": sum(x["bytes"] for x in entries)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(fingerprint(args.paths), indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()

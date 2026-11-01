#!/usr/bin/env python3
"""Validate production qualification output is separate from source and evidence paths."""
import argparse
from pathlib import Path

def guard(output, config, report, source_paths):
    target = Path(output).resolve()
    source_files = [Path(config).resolve()]
    for raw in source_paths:
        path = Path(raw).resolve()
        if not path.exists():
            raise ValueError(f"missing input path: {raw}")
        source_files.append(path)
    report_path = Path(report).resolve()
    if target == report_path or report_path in target.parents:
        raise ValueError("video output must be outside qualification evidence directory")
    for source in source_files:
        if target == source or (source.is_dir() and source in target.parents):
            raise ValueError(f"video output overlaps source input: {source}")
    if target.exists() or target.is_symlink():
        raise ValueError(f"video output already exists: {target}")
    return str(target)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output")
    p.add_argument("config")
    p.add_argument("report")
    p.add_argument("inputs", nargs="+")
    a = p.parse_args()
    print(guard(a.output, a.config, a.report, a.inputs))

if __name__ == "__main__":
    main()

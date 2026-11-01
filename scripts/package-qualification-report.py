#!/usr/bin/env python3
"""Create a compact review bundle from one qualification run (never include source media)."""
import argparse
import tarfile
from pathlib import Path

FILES = (
    "qualification-status.json", "summary.json", "summary.md",
    "failure-analysis.json",
)
RUN_FILES = (
    "measurements.csv", "process-memory.csv",
    "host-memory-before.txt", "host-memory-after.txt",
    "failure-diagnostics.json",
)
def package(report: Path, destination: Path) -> int:
    if not report.is_dir():
        raise ValueError("qualification directory not found")
    runs = [p for p in report.glob("run-*") if p.is_dir()]
    if len(runs) != 1:
        raise ValueError(f"expected exactly one benchmark run, found {len(runs)}")
    dest = destination.resolve()
    count = 0
    with tarfile.open(dest, "w:gz") as archive:
        for name in FILES:
            file = report/name
            if file.is_file() and not file.is_symlink():
                archive.add(file, arcname=name, recursive=False)
                count += 1
        for name in RUN_FILES:
            file = runs[0]/name
            if file.is_file() and not file.is_symlink():
                archive.add(file, arcname="benchmark/"+name, recursive=False)
                count += 1
    if not count:
        dest.unlink(missing_ok=True)
        raise ValueError("no diagnostic files available")
    return count

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("qualification_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args()
    try:
        n=package(args.qualification_directory, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Diagnostic bundle failed: {error}\n")
    print(f"Created {args.output} with {n} diagnostic files (no media or raw logs).")

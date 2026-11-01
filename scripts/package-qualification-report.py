#!/usr/bin/env python3
"""Create a compact review bundle from one qualification run (never include source media)."""
import argparse
import tarfile
import os
import tempfile
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
    runs = [p for p in report.glob("run-*") if p.is_dir() and not p.is_symlink()]
    if len(runs) != 1:
        raise ValueError(f"expected exactly one benchmark run, found {len(runs)}")
    dest = destination.absolute()
    if dest.exists():
        raise ValueError("refusing to overwrite an existing diagnostic archive")
    if dest.is_relative_to(report.resolve()):
        raise ValueError("archive destination must be outside the qualification report")
    count = 0
    with tempfile.NamedTemporaryFile(prefix=".qualification-",suffix=".tar.gz",dir=dest.parent,delete=False) as tmp:
        staging = Path(tmp.name)
    try:
        with tarfile.open(staging, "w:gz") as archive:
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
            raise ValueError("no diagnostic files available")
        os.link(staging,dest)  # atomic creation, fails if destination appeared concurrently
        return count
    finally:
        staging.unlink(missing_ok=True)

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

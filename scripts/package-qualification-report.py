#!/usr/bin/env python3
"""Create a compact diagnostic archive without including source media or raw logs."""
import argparse
import os
import stat
import tarfile
import tempfile
from pathlib import Path

FILES = ("qualification-status.json", "summary.json", "summary.md", "failure-analysis.json")
RUN_FILES = ("measurements.csv", "process-memory.csv", "host-memory-before.txt",
             "host-memory-after.txt", "failure-diagnostics.json")

# Diagnostic summaries should remain compact even if a report is unexpectedly huge.
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024


def _add_regular_file(archive: tarfile.TarFile, path: Path, name: str,
                      remaining_bytes: int) -> int | None:
    """Read a regular file through a no-follow descriptor, not a checked pathname."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        if path.is_symlink():
            raise ValueError(f"refusing symlinked diagnostic input: {path.name}") from exc
        raise
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"diagnostic input is not a regular file: {path.name}")
        if info.st_size > MAX_FILE_BYTES:
            raise ValueError(f"diagnostic input exceeds per-file size limit: {path.name}")
        if info.st_size > remaining_bytes:
            raise ValueError("diagnostic inputs exceed total size limit")
        member = tarfile.TarInfo(name)
        member.size = info.st_size
        member.mode = 0o600
        member.mtime = 0
        archive.addfile(member, source)
    return info.st_size


def package(report: Path, destination: Path) -> int:
    if report.is_symlink():
        raise ValueError("symlinked qualification directory is not allowed")
    if not report.is_dir():
        raise ValueError("qualification directory not found")
    report_root = report.resolve(strict=True)
    candidate_runs = list(report.glob("run-*"))
    if any(path.is_symlink() for path in candidate_runs):
        raise ValueError("symlinked benchmark run directory is not allowed")
    runs = [path for path in candidate_runs if path.is_dir()]
    if len(runs) != 1:
        raise ValueError(f"expected exactly one benchmark run, found {len(runs)}")

    destination = destination.absolute()
    dest_parent = destination.parent.resolve(strict=True)
    dest = dest_parent / destination.name
    if dest == report_root or report_root in dest.parents:
        raise ValueError("archive destination must be outside the qualification report")
    if dest.exists() or dest.is_symlink():
        raise ValueError("refusing to overwrite an existing diagnostic archive")

    count = 0
    total_bytes = 0
    with tempfile.NamedTemporaryFile(prefix=".qualification-", suffix=".tar.gz",
                                     dir=dest_parent, delete=False) as tmp:
        staging = Path(tmp.name)
    try:
        with tarfile.open(staging, "w:gz") as archive:
            for name in FILES:
                added = _add_regular_file(archive, report / name, name, MAX_TOTAL_BYTES - total_bytes)
                count += added is not None
                total_bytes += added or 0
            for name in RUN_FILES:
                added = _add_regular_file(archive, runs[0] / name, "benchmark/" + name, MAX_TOTAL_BYTES - total_bytes)
                count += added is not None
                total_bytes += added
        if not count:
            raise ValueError("no diagnostic files available")
        os.link(staging, dest, follow_symlinks=False)
        return count
    finally:
        staging.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("qualification_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        n = package(args.qualification_directory, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Diagnostic bundle failed: {error}\n")
    print(f"Created {args.output} with {n} diagnostic files (no media or raw logs).")

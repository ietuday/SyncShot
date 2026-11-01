#!/usr/bin/env python3
"""Validate and safely extract a verified SyncShot benchmark archive."""
import argparse
from pathlib import Path
import tarfile

PREFIX = "paired-qualification-evidence/"
MAX_FILES = 100
MAX_BYTES = 50 * 1024 * 1024


def extract_archive(archive, destination):
    """Extract only regular root-level evidence files, rejecting links and traversal."""
    destination = Path(destination)
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        seen = set()
        total = 0
        files = []
        for member in members:
            name = member.name
            if name in (PREFIX, PREFIX.rstrip("/")) and member.isdir():
                continue
            if not member.isfile() or not name.startswith(PREFIX):
                raise ValueError("Unsafe evidence archive member")
            relative = name[len(PREFIX):]
            if not relative or "/" in relative or "\\" in relative or relative in (".", ".."):
                raise ValueError("Unsafe evidence archive path")
            if relative in seen or len(seen) >= MAX_FILES:
                raise ValueError("Duplicate or excessive evidence files")
            seen.add(relative)
            if member.size < 0 or member.size > MAX_BYTES - total:
                raise ValueError("Archive exceeds maximum extracted size")
            total += member.size
            files.append((member, relative))
        if not {"run-manifest.json", "paired-performance-comparison.json"}.issubset(seen):
            raise ValueError("Missing required evidence files")
        destination.mkdir(parents=True, exist_ok=True)
        for member, name in files:
            source = tar.extractfile(member)
            if source is None:
                raise ValueError("Cannot read evidence member")
            with source, (destination / name).open("xb") as target:
                remaining = member.size
                while remaining:
                    chunk = source.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        raise ValueError("Truncated archive member")
                    target.write(chunk)
                    remaining -= len(chunk)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    extract_archive(args.archive, args.destination)


if __name__ == "__main__":
    main()

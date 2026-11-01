#!/usr/bin/env python3
"""Inspect Runway task statuses and optionally save completed MP4 clips.

Requires runwayml for live requests. No downloads without --download.
"""
import argparse
import ipaddress
import json
import os
import socket
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

MAX_CLIP_BYTES = 256 * 1024 * 1024

def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("task output must be an HTTPS URL without credentials")
    if parsed.port not in (None, 443):
        raise ValueError("nonstandard output URL port")
    host = parsed.hostname
    if host.lower() == "localhost" or host.lower().endswith(".local"):
        raise ValueError("local output URL refused")
    for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        address = ipaddress.ip_address(item[4][0])
        if not address.is_global:
            raise ValueError("non-public task output URL refused")
    return url

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirects are disabled for clip downloads")

def download(url, destination, opener=None):
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"refusing to overwrite {destination}")
    validate_url(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    opener = opener or urllib.request.build_opener(NoRedirect())
    fd, name = tempfile.mkstemp(prefix=".clip-", suffix=".part", dir=destination.parent)
    staging = Path(name)
    try:
        with os.fdopen(fd, "wb") as target:
            with opener.open(url, timeout=120) as source:
                count = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > MAX_CLIP_BYTES:
                        raise ValueError("clip exceeds maximum allowed download size")
                    target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        with staging.open("rb") as content:
            header = content.read(12)
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise ValueError("download is not an MP4 container")
        os.link(staging, destination)
    finally:
        staging.unlink(missing_ok=True)

def collect(tasks, client, outdir, should_download=False, fetcher=download):
    entries = tasks.get("clips")
    if tasks.get("mode") != "submitted" or not isinstance(entries, list) or not entries:
        raise ValueError("expected submitted animation task manifest")
    if len(entries) > 100:
        raise ValueError("too many animation tasks")
    results = []
    for entry in entries:
        task_id = entry.get("task_id")
        index = entry.get("scene")
        if not isinstance(task_id, str) or not task_id or not isinstance(index, int) or index < 1:
            raise ValueError("invalid task manifest entry")
        task = client.tasks.retrieve(task_id)
        status = str(task.status)
        item = {"scene": index, "task_id": task_id, "status": status}
        if status == "SUCCEEDED":
            outputs = getattr(task, "output", None)
            if not isinstance(outputs, (list, tuple)) or not outputs:
                raise ValueError(f"task {task_id} has no output")
            if should_download:
                destination = outdir / f"scene-{index:04d}.mp4"
                fetcher(outputs[0], destination)
                item["file"] = str(destination)
            else:
                item["download_available"] = True
        elif status in ("FAILED", "CANCELLED", "CANCELED"):
            item["error"] = str(getattr(task, "failure", None) or "generation failed")
        results.append(item)
    return {"clips": results}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--download", action="store_true", help="download successful clips")
    args = parser.parse_args(argv)
    try:
        if args.tasks.stat().st_size > 128 * 1024:
            raise ValueError("task manifest too large")
        if args.report.exists() or args.report.is_symlink():
            raise ValueError("refusing to overwrite status report")
        if not os.environ.get("RUNWAYML_API_SECRET"):
            raise ValueError("RUNWAYML_API_SECRET required to query task status")
        from runwayml import RunwayML
        report = collect(json.loads(args.tasks.read_text(encoding="utf-8")),
                         RunwayML(), args.output_dir, args.download)
        with args.report.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
        print(f"Checked {len(report['clips'])} animation tasks")
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(1, f"Animation retrieval failed: {exc}\n")

if __name__ == "__main__":
    main()

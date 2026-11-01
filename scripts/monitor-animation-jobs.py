#!/usr/bin/env python3
"""Monitor existing Runway animation jobs without creating paid generation tasks."""
import argparse
import json
import os
import time
from pathlib import Path

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELED", "CANCELLED"}
ACTIVE = {"PENDING", "THROTTLED", "RUNNING"}
VALID = TERMINAL | ACTIVE

def validate_manifest(data):
    entries = data.get("clips")
    if data.get("mode") != "submitted" or not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise ValueError("expected submitted manifest containing 1..100 clips")
    seen = set()
    for entry in entries:
        scene, task_id = entry.get("scene"), entry.get("task_id")
        if not isinstance(scene, int) or isinstance(scene, bool) or scene < 1 or scene in seen:
            raise ValueError("invalid or duplicate scene index")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("invalid task ID")
        seen.add(scene)
    return entries

def snapshot(entries, client):
    result = []
    for entry in entries:
        task = client.tasks.retrieve(entry["task_id"])
        status = str(task.status).upper()
        if status not in VALID:
            raise ValueError(f"unrecognized provider status {status}")
        row = {"scene": entry["scene"], "task_id": entry["task_id"], "status": status}
        if status in ("FAILED", "CANCELED", "CANCELLED"):
            row["failure"] = str(getattr(task, "failure", None) or "task did not complete")
        result.append(row)
    return {"mode": "status", "clips": result, "complete": all(row["status"] in TERMINAL for row in result)}

def poll(entries, client, interval=30, max_checks=1, sleeper=time.sleep):
    if not 1 <= max_checks <= 120 or not 1 <= interval <= 3600:
        raise ValueError("interval must be 1..3600 and max-checks 1..120")
    result = None
    for attempt in range(max_checks):
        result = snapshot(entries, client)
        if result["complete"]:
            break
        if attempt + 1 < max_checks:
            sleeper(interval)
    return result

def save_report(path, result):
    if path.exists() or path.is_symlink():
        raise FileExistsError("refusing to overwrite status report")
    # Exclusive creation prevents overwriting a concurrent writer.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--max-checks", type=int, default=1)
    args = parser.parse_args(argv)
    try:
        if args.tasks.stat().st_size > 128 * 1024:
            raise ValueError("task manifest too large")
        entries = validate_manifest(json.loads(args.tasks.read_text(encoding="utf-8")))
        if not os.environ.get("RUNWAYML_API_SECRET"):
            raise ValueError("RUNWAYML_API_SECRET is required")
        from runwayml import RunwayML
        outcome = poll(entries, RunwayML(), args.interval, args.max_checks)
        save_report(args.report, outcome)
        counts = {status: sum(x["status"] == status for x in outcome["clips"]) for status in VALID}
        print(f"Checked {len(entries)} existing tasks; complete={outcome['complete']}; counts={counts}")
        return 0 if outcome["complete"] and all(x["status"] == "SUCCEEDED" for x in outcome["clips"]) else 2
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(1, f"Animation monitor failed: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())

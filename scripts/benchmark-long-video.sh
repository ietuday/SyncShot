#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-./output/benchmarks}"
mkdir -p "$OUT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$OUT/$STAMP"
mkdir -p "$RUN_DIR"
go build -o "$RUN_DIR/syncshot" ./cmd/syncshot
ffmpeg -version | head -n 1 > "$RUN_DIR/environment.txt"
go version >> "$RUN_DIR/environment.txt"
printf "start_utc,elapsed_seconds,max_rss_kb,exit_code,output_bytes\n" > "$RUN_DIR/measurements.csv"
start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
set +e
/usr/bin/time -f "%e,%M,%x" -o "$RUN_DIR/resource.txt" "$RUN_DIR/syncshot" > "$RUN_DIR/run.log" 2>&1
status=$?
set -e
read -r numbers < "$RUN_DIR/resource.txt"
size=0
if [[ -f ./output/video/final.mp4 ]]; then size="$(stat -c %s ./output/video/final.mp4)"; fi
printf "%s,%s,%s\n" "$start" "$numbers" "$size" >> "$RUN_DIR/measurements.csv"
echo "Exit: $status; logs: $RUN_DIR"
exit "$status"

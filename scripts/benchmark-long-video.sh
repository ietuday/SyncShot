#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-./output/benchmarks}"
if (( $# > 0 )); then shift; fi
CLI_ARGS=("$@")
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
RUN_DIR="$(mktemp -d "$OUT/run-XXXXXXXX")"
go build -o "$RUN_DIR/syncshot" ./cmd/syncshot
ffmpeg -version | head -n 1 > "$RUN_DIR/environment.txt"
go version >> "$RUN_DIR/environment.txt"
ffprobe -version | head -n 1 >> "$RUN_DIR/environment.txt"
printf "%s\n" "$(git rev-parse HEAD 2>/dev/null || echo unknown)" > "$RUN_DIR/source-commit.txt"
{ uname -srm; nproc 2>/dev/null || true; } > "$RUN_DIR/machine.txt"
# Explicit workload ID must encode media, render settings and hardware for comparisons.
printf "%s\n" "${SYNC_SHOT_BENCHMARK_WORKLOAD_ID:-unlabeled}" > "$RUN_DIR/workload-id.txt"
if [[ -n "${SYNC_SHOT_BENCHMARK_INPUTS:-}" ]]; then
  IFS=":" read -r -a INPUT_PATHS <<< "$SYNC_SHOT_BENCHMARK_INPUTS"
  python3 "$ROOT/scripts/fingerprint-inputs.py" --output "$RUN_DIR/inputs-fingerprint.json" "${INPUT_PATHS[@]}"
fi
printf "%q " "$RUN_DIR/syncshot" "${CLI_ARGS[@]}" > "$RUN_DIR/command.txt"
printf "\\n" >> "$RUN_DIR/command.txt"
printf 'timestamp_utc,active_processes,total_rss_kb,ffmpeg_rss_kb\n' > "$RUN_DIR/process-memory.csv"
printf 'start_utc,elapsed_seconds,peak_process_tree_rss_kb,peak_ffmpeg_rss_kb,exit_code,output_bytes\n' > "$RUN_DIR/measurements.csv"
start="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
started="$(date +%s)"
# Output path may be overridden for benchmark runs.
OUTPUT_VIDEO="${SYNC_SHOT_BENCHMARK_OUTPUT:-./output/video/final.mp4}"
original_present=0
original_signature=""
if [[ -f "$OUTPUT_VIDEO" ]]; then
  original_present=1
  original_signature="$(stat -c '%d:%i:%s:%Y:%Z' "$OUTPUT_VIDEO")"
fi
"$RUN_DIR/syncshot" "${CLI_ARGS[@]}" > "$RUN_DIR/run.log" 2>&1 &
root_pid=$!
cleanup() {
  if kill -0 "$root_pid" 2>/dev/null; then
    pkill -TERM -P "$root_pid" 2>/dev/null || true
    kill -TERM "$root_pid" 2>/dev/null || true
    wait "$root_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# Enumerate descendants recursively; /proc/<pid>/status VmRSS is instantaneous.
descendants() {
  local parent="$1" child
  for child in $(pgrep -P "$parent" 2>/dev/null || true); do
    printf '%s\n' "$child"
    descendants "$child"
  done
}
peak_tree=0
peak_ffmpeg=0
while kill -0 "$root_pid" 2>/dev/null; do
  tree_rss=0
  ffmpeg_rss=0
  count=0
  for pid in "$root_pid" $(descendants "$root_pid"); do
    [[ -r "/proc/$pid/status" ]] || continue
    rss="$(awk '/^VmRSS:/ {print $2;exit}' "/proc/$pid/status" 2>/dev/null || true)"
    [[ "$rss" =~ ^[0-9]+$ ]] || continue
    ((tree_rss+=rss)) || true
    ((count+=1)) || true
    command_name="$(cat "/proc/$pid/comm" 2>/dev/null || true)"
    if [[ "$command_name" == ffmpeg ]]; then
      ((ffmpeg_rss+=rss)) || true
    fi
  done
  ((tree_rss>peak_tree)) && peak_tree="$tree_rss" || true
  ((ffmpeg_rss>peak_ffmpeg)) && peak_ffmpeg="$ffmpeg_rss" || true
  printf '%s,%s,%s,%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$count" "$tree_rss" "$ffmpeg_rss" >> "$RUN_DIR/process-memory.csv"
  sleep 1
done
set +e
wait "$root_pid"
status=$?
set -e
elapsed="$(($(date +%s)-started))"
size=0
if [[ "$status" -eq 0 ]]; then
  if size="$(bash "$ROOT/scripts/verify-benchmark-output.sh" "$OUTPUT_VIDEO" "$original_signature" "$RUN_DIR/output-duration.txt")"; then
    :
  else
    status=1
    size=0
  fi
fi
printf '%s,%s,%s,%s,%s,%s\n' "$start" "$elapsed" "$peak_tree" "$peak_ffmpeg" "$status" "$size" >> "$RUN_DIR/measurements.csv"
if [[ "$status" -ne 0 ]]; then
  python3 "$ROOT/scripts/summarize-render-failure.py" "$RUN_DIR" "$status" || true
fi
echo "Exit: $status; peak tree RSS: $peak_tree KiB; peak FFmpeg RSS: $peak_ffmpeg KiB; logs: $RUN_DIR"
exit "$status"

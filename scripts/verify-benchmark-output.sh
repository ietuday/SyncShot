#!/usr/bin/env bash
set -euo pipefail
# Usage: verify-benchmark-output.sh PATH PREVIOUS_SIGNATURE OUTPUT_DURATION_FILE
# Prints the verified file size only. Empty previous signature means no previous output.
video="$1"
previous="$2"
duration_file="$3"
[[ -s "$video" ]] || { echo "Benchmark failed: output missing or empty: $video" >&2; exit 1; }
current="$(stat -c '%d:%i:%s:%Y:%Z' "$video")"
if [[ -n "$previous" && "$current" == "$previous" ]]; then
 echo "Benchmark failed: output unchanged: $video" >&2; exit 1
fi
ffprobe -v error -show_entries format=duration -of default=nokey=1:noprint_wrappers=1 "$video" > "$duration_file" || { echo "Benchmark failed: ffprobe error: $video" >&2; exit 1; }
awk 'NR==1 {if ($1+0<=0) exit 1; ok=1} END {if (!ok) exit 1}' "$duration_file" || { echo "Benchmark failed: invalid duration: $video" >&2; exit 1; }
stat -c %s "$video"

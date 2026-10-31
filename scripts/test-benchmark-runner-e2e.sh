#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/audio" "$TMP/images" "$TMP/reports"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=2' -c:a libmp3lame "$TMP/audio/narration.mp3"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=blue:s=320x180' -frames:v 1 "$TMP/images/001.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=red:s=320x180' -frames:v 1 "$TMP/images/002.png"
cat > "$TMP/config.json" <<EOF
{
  "AudioDir": "$TMP/audio",
  "ImagesDir": "$TMP/images",
  "OutVideoPath": "$TMP/final.mp4",
  "OutShortsDir": "$TMP/shorts",
  "WorkDir": "$TMP/work",
  "ClipSeconds": 0,
  "PreviewSeconds": 0,
  "RenderProfile": "720p",
  "MaxWorkers": 2
}
EOF
SYNC_SHOT_BENCHMARK_OUTPUT="$TMP/final.mp4" \
SYNC_SHOT_BENCHMARK_WORKLOAD_ID="ci-2s-720p" \
SYNC_SHOT_BENCHMARK_INPUTS="$TMP/audio:$TMP/images:$TMP/config.json" \
bash scripts/benchmark-long-video.sh "$TMP/reports" --config "$TMP/config.json" --timeout 5m
python3 scripts/summarize-benchmarks.py "$TMP/reports" --json "$TMP/summary.json"
python3 - "$TMP/summary.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding="utf-8"))
assert len(data)==1, data
run=data[0]
assert run["output_bytes"]>0,run
assert 1<float(run["duration_seconds"])<5,run
assert len(run["input_fingerprint"])==64,run
assert run["workload_id"]=="ci-2s-720p",run
print("Benchmark end-to-end smoke test passed")
PY
# Persist selected evidence outside the automatically deleted temp workspace.
if [[ -n "${SYNC_SHOT_BENCHMARK_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR"
  cp "$TMP/summary.json" "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/summary.json"
  find "$TMP/reports" -name measurements.csv -exec cp {} "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/measurements.csv" \;
  find "$TMP/reports" -name process-memory.csv -exec cp {} "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/process-memory.csv" \;
fi

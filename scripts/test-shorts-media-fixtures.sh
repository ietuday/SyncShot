#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/audio" "$WORK/images" "$WORK/reports"
# Complex generated image sources vary in geometry and frames; no copyrighted assets.
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=1280x720:rate=1' -frames:v 1 "$WORK/images/001.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'smptebars=size=1280x720:rate=1' -frames:v 1 "$WORK/images/002.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'mandelbrot=size=1280x720:rate=1' -frames:v 1 "$WORK/images/003.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=330:duration=18' -af 'volume=0.6' -c:a libmp3lame "$WORK/audio/narration.mp3"
cat > "$WORK/config.json" <<EOF
{"AudioDir":"$WORK/audio","ImagesDir":"$WORK/images","OutVideoPath":"$WORK/final.mp4","OutShortsDir":"$WORK/shorts","WorkDir":"$WORK/work","ClipSeconds":8,"SmartShortsEnabled":true,"SmartShortsCrop":"center","RenderProfile":"720p","MaxWorkers":2,"CinematicChunkScenes":4}
EOF
SYNC_SHOT_BENCHMARK_OUTPUT="$WORK/final.mp4" \
SYNC_SHOT_BENCHMARK_WORKLOAD_ID="ci-18s-varied-fixtures-720p" \
SYNC_SHOT_BENCHMARK_INPUTS="$WORK/audio:$WORK/images:$WORK/config.json" \
bash scripts/benchmark-long-video.sh "$WORK/reports" --config "$WORK/config.json" --timeout 8m
python3 scripts/summarize-benchmarks.py "$WORK/reports" --json "$WORK/summary.json"
python3 scripts/check-media-quality.py "$WORK/final.mp4" --width 1280 --height 720 --min-duration 15 --max-duration 21 > "$WORK/media-quality.json"
python3 scripts/check-audio-integrity.py "$WORK/final.mp4" > "$WORK/audio-integrity.json"
python3 scripts/check-shorts-quality.py "$WORK/shorts" --max-duration 8 --evidence "$WORK/shorts-quality.json"
if [[ -n "${SYNC_SHOT_BENCHMARK_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR"
  cp "$WORK/summary.json" "$WORK/media-quality.json" "$WORK/audio-integrity.json" "$WORK/shorts-quality.json" "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/"
fi
echo "Varied-fixture video qualification passed"

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DURATION="${SYNC_SHOT_QUALIFICATION_SECONDS:-60}"
case "$DURATION" in
  ''|*[!0-9]*) echo "duration must be an integer" >&2; exit 2;;
esac
if (( DURATION < 10 || DURATION > 600 )); then
 echo "qualification duration must be 10..600 seconds" >&2; exit 2
fi
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/audio" "$WORK/images" "$WORK/reports"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "sine=frequency=440:duration=$DURATION" -c:a libmp3lame "$WORK/audio/narration.mp3"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=blue:s=320x180' -frames:v 1 "$WORK/images/001.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=red:s=320x180' -frames:v 1 "$WORK/images/002.png"
cat > "$WORK/config.json" <<EOF
{"AudioDir":"$WORK/audio","ImagesDir":"$WORK/images","OutVideoPath":"$WORK/final.mp4","OutShortsDir":"$WORK/shorts","WorkDir":"$WORK/work","ClipSeconds":0,"RenderProfile":"720p","MaxWorkers":2,"CinematicChunkScenes":4}
EOF
SYNC_SHOT_BENCHMARK_OUTPUT="$WORK/final.mp4" \
SYNC_SHOT_BENCHMARK_WORKLOAD_ID="qualification-${DURATION}s-720p-chunk4" \
SYNC_SHOT_BENCHMARK_INPUTS="$WORK/audio:$WORK/images:$WORK/config.json" \
bash scripts/benchmark-long-video.sh "$WORK/reports" --config "$WORK/config.json" --timeout 25m
python3 scripts/summarize-benchmarks.py "$WORK/reports" --json "$WORK/summary.json"
python3 scripts/check-media-quality.py "$WORK/final.mp4" --width 1280 --height 720 --min-duration "$((DURATION-3))" --max-duration "$((DURATION+3))" > "$WORK/media-quality.json"
if [[ -n "${SYNC_SHOT_BENCHMARK_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR"
  cp "$WORK/summary.json" "$WORK/media-quality.json" "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/"
fi
echo "Medium-video qualification passed for ${DURATION}s"

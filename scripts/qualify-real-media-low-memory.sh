#!/usr/bin/env bash
# Manually qualify the original audio/images without modifying source assets.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
AUDIO_DIR="${1:-inputs/audio}"
IMAGE_DIR="${2:-inputs/images}"
REPORT_DIR="${3:-output/real-media-qualification}"
mkdir -p "$REPORT_DIR"
REPORT_DIR="$(realpath "$REPORT_DIR")"
# The qualification workspace must not be inside input directories.
# Otherwise generated assets can contaminate the media scan/fingerprint.

AUDIO_DIR="$(realpath "$AUDIO_DIR")"
IMAGE_DIR="$(realpath "$IMAGE_DIR")"
test -d "$AUDIO_DIR" || { echo "Audio directory missing: $AUDIO_DIR" >&2; exit 2; }
test -d "$IMAGE_DIR" || { echo "Image directory missing: $IMAGE_DIR" >&2; exit 2; }
for source in "$AUDIO_DIR" "$IMAGE_DIR"; do
  case "$REPORT_DIR/" in
    "$source/"*) echo "Report directory cannot be inside an input directory: $source" >&2; exit 2;;
  esac
done
WORK="$(mktemp -d "$REPORT_DIR/work-XXXXXXXX")"
trap 'rm -rf "$WORK"' EXIT
OUTPUT="$WORK/qualified.mp4"
python3 - "$WORK/config.json" "$AUDIO_DIR" "$IMAGE_DIR" "$WORK" "$OUTPUT" <<'PY'
import json,sys
path,audio,images,work,output=sys.argv[1:]
config=dict(AudioDir=audio, ImagesDir=images, OutVideoPath=output,
            OutShortsDir=work+"/shorts",WorkDir=work+"/work",
            FPS=24,SecondsPerImage=3,ClipSeconds=0,MaxWorkers=1,
            CinematicEnabled=True,CinematicCrossfade=0.5,
            CinematicMotion="zoom_in",CinematicAutoSceneSeconds=30,
            CinematicChunkScenes=1,RenderProfile="720p")
with open(path,"w") as handle:json.dump(config,handle,indent=2)
PY
export SYNC_SHOT_BENCHMARK_WORKLOAD_ID="real-media-720p-24fps-1chunk-$(date -u +%Y%m%d)"
export SYNC_SHOT_BENCHMARK_INPUTS="$WORK/config.json:$AUDIO_DIR:$IMAGE_DIR"
export SYNC_SHOT_BENCHMARK_OUTPUT="$OUTPUT"
RUNS_BEFORE="$(find "$REPORT_DIR" -mindepth 1 -maxdepth 1 -type d -name "run-*" -printf "%f\\n" | sort)"
bash scripts/benchmark-long-video.sh "$REPORT_DIR" --config "$WORK/config.json" --memory-mode low --output "$OUTPUT"
RUNS_AFTER="$(find "$REPORT_DIR" -mindepth 1 -maxdepth 1 -type d -name "run-*" -printf "%f\\n" | sort)"
RUN_NAME="$(comm -13 <(printf "%s\\n" "$RUNS_BEFORE") <(printf "%s\\n" "$RUNS_AFTER") | head -n 1)"
if [[ -z "$RUN_NAME" ]]; then echo "Benchmark did not create a new report directory" >&2; exit 1; fi
RUN_REPORT="$REPORT_DIR/$RUN_NAME"
python3 scripts/check-low-memory-benchmark.py "$RUN_REPORT/.." --max-ffmpeg-rss-mib "${SYNC_SHOT_MAX_FFMPEG_RSS_MIB:-8192}"
python3 scripts/check-av-sync.py "$OUTPUT" --max-drift-seconds 0.5
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$OUTPUT" | grep -qx "1280x720"
echo "Real-media qualification passed. Measurements and logs: $RUN_REPORT"

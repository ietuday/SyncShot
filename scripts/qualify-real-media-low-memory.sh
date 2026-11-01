#!/usr/bin/env bash
# Manually qualify the original audio/images without modifying source assets.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
AUDIO_DIR="${1:-inputs/audio}"
IMAGE_DIR="${2:-inputs/images}"
REPORT_DIR="${3:-output/real-media-qualification}"
AUDIO_DIR="$(realpath "$AUDIO_DIR")"
IMAGE_DIR="$(realpath "$IMAGE_DIR")"
test -d "$AUDIO_DIR" || { echo "Audio directory missing: $AUDIO_DIR" >&2; exit 2; }
test -d "$IMAGE_DIR" || { echo "Image directory missing: $IMAGE_DIR" >&2; exit 2; }
REPORT_DIR="$(realpath -m "$REPORT_DIR")"
# The qualification workspace must not be inside input directories.
# Otherwise generated assets can contaminate the media scan/fingerprint.

for source in "$AUDIO_DIR" "$IMAGE_DIR"; do
  case "$REPORT_DIR/" in
    "$source/"*) echo "Report directory cannot be inside an input directory: $source" >&2; exit 2;;
  esac
done
# Validate the destination before writing any generated files.
mkdir -p "$REPORT_DIR"
for command in go ffmpeg ffprobe python3; do
  command -v "$command" >/dev/null 2>&1 || { echo "Required command missing: $command" >&2; exit 2; }
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
RUN_REPORT="$(mktemp -d "$REPORT_DIR/qualification-XXXXXXXX")"
# Preserve benchmark evidence even if rendering or a later quality gate fails.
on_qualification_exit() {
  status="$1"
  trap - EXIT
  if [[ -d "$RUN_REPORT" ]]; then
    python3 scripts/summarize-real-media-qualification.py "$RUN_REPORT" || true
    if (( status != 0 )); then
      echo "Qualification failed (exit $status). Reports and logs: $RUN_REPORT" >&2
    fi
  fi
  rm -rf -- "$WORK"
}
trap 'on_qualification_exit "$?"' EXIT
bash scripts/benchmark-long-video.sh "$RUN_REPORT" --config "$WORK/config.json" --memory-mode low --output "$OUTPUT"
python3 scripts/summarize-real-media-qualification.py "$RUN_REPORT"
python3 scripts/check-low-memory-benchmark.py "$RUN_REPORT" --max-ffmpeg-rss-mib "${SYNC_SHOT_MAX_FFMPEG_RSS_MIB:-8192}"
python3 scripts/check-av-sync.py "$OUTPUT" --max-drift-seconds 0.5
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$OUTPUT" | grep -qx "1280x720"
echo "Real-media qualification passed. Measurements and logs: $RUN_REPORT/run-*"

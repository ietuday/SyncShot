#!/usr/bin/env bash
# Manual 15-minute / 10-image memory qualification; never run on normal PR CI.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REPORT_ROOT="${1:-./output/qualification-15m}"
mkdir -p "$REPORT_ROOT"
REPORT_ROOT="$(cd "$REPORT_ROOT" && pwd)"
WORK="$(mktemp -d "$REPORT_ROOT/work-XXXXXXXX")"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/inputs/audio" "$WORK/inputs/images"
for i in $(seq -w 1 10); do
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i "color=c=blue:s=1280x720" -frames:v 1 "$WORK/inputs/images/$i.png"
done
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anullsrc=r=44100:cl=stereo" -t 925.36 -c:a aac -b:a 64k "$WORK/inputs/audio/narration.m4a"
python3 - "$WORK" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
config={
    "AudioDir":str(root/"inputs/audio"),
    "ImagesDir":str(root/"inputs/images"),
    "WorkDir":str(root/"work"),
    "OutVideoPath":str(root/"final.mp4"),
    "OutShortsDir":str(root/"shorts"),
    "ClipSeconds":0,
    "CinematicEnabled":True,
    "CinematicAutoSceneSeconds":30,
    "CinematicCrossfade":0.5,
    "CinematicMotion":"zoom_in",
    "CinematicChunkScenes":1,
    "RenderProfile":"720p",
    "MaxWorkers":1,
    "FPS":24,
}
(root/"config.json").write_text(json.dumps(config,indent=2)+"\n")
PY
export SYNC_SHOT_BENCHMARK_WORKLOAD_ID="synthetic-10-images-925s-720p-1scene"
export SYNC_SHOT_BENCHMARK_INPUTS="$WORK/config.json:$WORK/inputs/audio/narration.m4a:$WORK/inputs/images"
export SYNC_SHOT_BENCHMARK_OUTPUT="$WORK/final.mp4"
bash scripts/benchmark-long-video.sh "$REPORT_ROOT" --config "$WORK/config.json" --memory-mode low --output "$WORK/final.mp4"
python3 scripts/check-low-memory-benchmark.py "$REPORT_ROOT" --max-ffmpeg-rss-mib "${SYNC_SHOT_MAX_FFMPEG_RSS_MIB:-8192}"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$WORK/final.mp4" | grep -qx '1280x720'
duration="$(ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 "$WORK/final.mp4")"
awk -v value="$duration" 'BEGIN { exit !(value > 924 && value < 927) }'
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of csv=p=0 "$WORK/final.mp4" | grep -qx aac
python3 scripts/check-av-sync.py "$WORK/final.mp4" --max-drift-seconds 0.5
echo "15-minute low-memory video qualification passed. Inspect measured peak RAM and elapsed time in $REPORT_ROOT/run-*/measurements.csv"

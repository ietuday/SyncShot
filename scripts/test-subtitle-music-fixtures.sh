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
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=330:duration=18' -af "volume=0.6,volume=0:enable='between(t,6,11)'" -c:a libmp3lame "$WORK/audio/narration.mp3"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=220:duration=18' -af 'volume=0.1' -c:a libmp3lame "$WORK/music.mp3"
cat > "$WORK/captions.srt" <<'SRT'
1
00:00:01,000 --> 00:00:05,000
Subtitle and music integration

2
00:00:08,000 --> 00:00:12,000
Second caption in the timeline
SRT
cat > "$WORK/config.json" <<EOF
{"AudioDir":"$WORK/audio","ImagesDir":"$WORK/images","OutVideoPath":"$WORK/final.mp4","OutShortsDir":"$WORK/shorts","WorkDir":"$WORK/work","ClipSeconds":0,"RenderProfile":"720p","MaxWorkers":2,"CinematicChunkScenes":4,"SubtitleMode":"import","SubtitleSRTPath":"$WORK/captions.srt","MusicPath":"$WORK/music.mp3","MusicVolume":0.15,"MusicDucking":true}
EOF
SYNC_SHOT_BENCHMARK_OUTPUT="$WORK/final.mp4" \
SYNC_SHOT_BENCHMARK_WORKLOAD_ID="ci-18s-subtitles-music-720p" \
SYNC_SHOT_BENCHMARK_INPUTS="$WORK/audio:$WORK/images:$WORK/config.json:$WORK/music.mp3:$WORK/captions.srt" \
bash scripts/benchmark-long-video.sh "$WORK/reports" --config "$WORK/config.json" --timeout 8m
# Render a matched no-ducking reference using identical generated source media.
python3 - "$WORK/config.json" "$WORK/reference-config.json" "$WORK/reference.mp4" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding="utf-8"))
data["MusicDucking"]=False
data["OutVideoPath"]=sys.argv[3]
json.dump(data,open(sys.argv[2],"w",encoding="utf-8"))
PY
SYNC_SHOT_BENCHMARK_OUTPUT="$WORK/reference.mp4" \
SYNC_SHOT_BENCHMARK_WORKLOAD_ID="ci-18s-subtitles-music-reference-720p" \
bash scripts/benchmark-long-video.sh "$WORK/reference-reports" --config "$WORK/reference-config.json" --timeout 8m
python3 scripts/check-ducking-attenuation.py "$WORK/reference.mp4" "$WORK/final.mp4" --start 2 --seconds 3 --tone-hz 220 --minimum-reduction-db 2 > "$WORK/ducking-attenuation.json"
python3 scripts/check-ducking-recovery.py "$WORK/reference.mp4" "$WORK/final.mp4" > "$WORK/ducking-recovery.json"
python3 scripts/summarize-benchmarks.py "$WORK/reports" --json "$WORK/summary.json"
python3 scripts/check-media-quality.py "$WORK/final.mp4" --width 1280 --height 720 --min-duration 15 --max-duration 21 > "$WORK/media-quality.json"
python3 scripts/check-audio-integrity.py "$WORK/final.mp4" > "$WORK/audio-integrity.json"
python3 scripts/check-subtitle-cue-timing.py "$WORK/captions.srt" "$WORK/final.mp4" --output "$WORK/subtitle-cues.json"
if [[ -n "${SYNC_SHOT_BENCHMARK_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR"
  cp "$WORK/summary.json" "$WORK/media-quality.json" "$WORK/audio-integrity.json" "$WORK/subtitle-cues.json" "$WORK/ducking-attenuation.json" "$WORK/ducking-recovery.json" "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/"
fi
echo "Subtitle and music integration qualification passed"

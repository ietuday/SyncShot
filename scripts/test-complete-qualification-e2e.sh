#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/audio" "$WORK/images" "$WORK/evidence"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=1280x720:rate=1' -frames:v 1 "$WORK/images/001.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'smptebars=size=1280x720:rate=1' -frames:v 1 "$WORK/images/002.png"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=6' -c:a libmp3lame "$WORK/audio/narration.mp3"
cat > "$WORK/config.json" <<EOF
{"AudioDir":"$WORK/audio","ImagesDir":"$WORK/images","OutVideoPath":"$WORK/final.mp4","OutShortsDir":"$WORK/shorts","WorkDir":"$WORK/work","ClipSeconds":0,"RenderProfile":"720p","MaxWorkers":2,"CinematicChunkScenes":4}
EOF
SYNC_SHOT_BENCHMARK_WORKLOAD_ID="ci-6s-complete-qualification-720p" \
SYNC_SHOT_BENCHMARK_INPUTS="$WORK/audio:$WORK/images:$WORK/config.json" \
SYNC_SHOT_EXPECT_WIDTH=1280 SYNC_SHOT_EXPECT_HEIGHT=720 \
SYNC_SHOT_MIN_DURATION=4 SYNC_SHOT_MAX_DURATION=9 \
SYNC_SHOT_QUALIFICATION_TIMEOUT=8m \
bash scripts/qualify-production-media.sh "$WORK/config.json" "$WORK/final.mp4" "$WORK/evidence"
python3 - "$WORK/evidence" "$WORK/final.mp4" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
reports=list(root.glob("qualification-*"))
assert len(reports)==1, f"expected one isolated report, got {len(reports)}"
report=reports[0]
for filename in ("status.json","preflight-summary.json","input-audit.json","media-decode.json",
                 "inputs-fingerprint.json","qualification-summary.json","media-quality.json","audio-integrity.json"):
    assert (report/filename).is_file(), f"missing {filename}"
status=json.loads((report/"status.json").read_text())
assert status["status"]=="success" and status["stage"]=="complete" and status["exit_code"]==0, status
preflight=json.loads((report/"preflight-summary.json").read_text())
assert preflight["decoded_file_count"]==3, preflight
assert preflight["audio_file_count"]==1 and preflight["image_file_count"]==2, preflight
assert pathlib.Path(sys.argv[2]).stat().st_size>0
print("Full qualification E2E passed; status and evidence verified")
PY
if [[ -n "${SYNC_SHOT_BENCHMARK_EVIDENCE_DIR:-}" ]]; then
  mkdir -p "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR"
  cp "$WORK/evidence"/qualification-*/{status.json,preflight-summary.json,qualification-summary.json,media-quality.json,audio-integrity.json} "$SYNC_SHOT_BENCHMARK_EVIDENCE_DIR/"
fi

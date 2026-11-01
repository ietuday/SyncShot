#!/usr/bin/env bash
# Short end-to-end smoke test for the real-media qualification wrapper.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
mkdir -p "$TEMP/audio" "$TEMP/images"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=3' -c:a pcm_s16le "$TEMP/audio/voice.wav"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=blue:s=320x180' -frames:v 1 "$TEMP/images/a.png"
# The wrapper must generate and check output without modifying original media.
before_audio="$(sha256sum "$TEMP/audio/voice.wav" | cut -d' ' -f1)"
before_image="$(sha256sum "$TEMP/images/a.png" | cut -d' ' -f1)"
SYNC_SHOT_KEEP_QUALIFIED_VIDEO=1 SYNC_SHOT_MAX_FFMPEG_RSS_MIB=8192 bash scripts/qualify-real-media-low-memory.sh "$TEMP/audio" "$TEMP/images" "$TEMP/reports"
test "$before_audio" = "$(sha256sum "$TEMP/audio/voice.wav" | cut -d' ' -f1)"
test "$before_image" = "$(sha256sum "$TEMP/images/a.png" | cut -d' ' -f1)"
count="$(find "$TEMP/reports" -maxdepth 1 -type d -name 'qualification-*' | wc -l)"
test "$count" -eq 1
report="$(find "$TEMP/reports" -maxdepth 1 -type d -name 'qualification-*' -print -quit)"
python3 - "$report" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
summary=json.loads((root/"summary.json").read_text())
assert summary["status"]=="passed", summary
assert summary["output_bytes"]>0, summary
assert summary["peak_ffmpeg_rss_mib"]>0, summary
assert (root/"summary.md").exists()
assert (root/"qualified.mp4").stat().st_size > 0
final_status=json.loads((root/"qualification-status.json").read_text())
assert final_status["status"]=="passed", final_status
assert final_status["exit_code"]==0, final_status
assert len(list(root.glob("run-*/measurements.csv")))==1
PY
echo "Real-media qualification end-to-end smoke passed"

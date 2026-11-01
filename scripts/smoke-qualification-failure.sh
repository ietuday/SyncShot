#!/usr/bin/env bash
# Exercise a validation failure after a successful short render.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
mkdir -p "$TEMP/audio" "$TEMP/images"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=3' -c:a pcm_s16le "$TEMP/audio/voice.wav"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=blue:s=320x180' -frames:v 1 "$TEMP/images/a.png"
set +e
SYNC_SHOT_MAX_FFMPEG_RSS_MIB=0.000001 bash scripts/qualify-real-media-low-memory.sh "$TEMP/audio" "$TEMP/images" "$TEMP/reports" >"$TEMP/stdout" 2>"$TEMP/stderr"
status=$?
set -e
if (( status == 0 )); then echo "Expected memory-gate failure" >&2; exit 1; fi
report="$(find "$TEMP/reports" -mindepth 1 -maxdepth 1 -type d -name 'qualification-*' -print -quit)"
test -n "$report"
python3 - "$report" "$status" <<'PY'
import json, pathlib, sys
root=pathlib.Path(sys.argv[1])
code=int(sys.argv[2])
final=json.loads((root/"qualification-status.json").read_text())
assert final["status"]=="failed",final
assert final["exit_code"]==code,final
assert final["last_stage"]=="memory",final
failure=json.loads((root/"failure-analysis.json").read_text())
assert failure["category"]=="memory_budget_exceeded",failure
assert (root/"summary.json").exists()
assert not (root/"qualified.mp4").exists()
PY
echo "Qualification post-render failure recovery verified"

# Invalid input media must not result in a qualified output.
mkdir -p "$TEMP/bad-audio" "$TEMP/bad-images"
printf 'not-an-audio-file' > "$TEMP/bad-audio/voice.wav"
cp "$TEMP/images/a.png" "$TEMP/bad-images/a.png"
set +e
bash scripts/qualify-real-media-low-memory.sh "$TEMP/bad-audio" "$TEMP/bad-images" "$TEMP/bad-reports" >"$TEMP/bad-stdout" 2>"$TEMP/bad-stderr"
bad_status=$?
set -e
if (( bad_status == 0 )); then echo "Corrupt input media unexpectedly passed" >&2; exit 1; fi
if find "$TEMP/bad-reports" -name qualified.mp4 -print -quit | grep -q .; then
  echo "Invalid-media qualification retained video" >&2; exit 1
fi
echo "Qualification invalid-media failure checks passed"

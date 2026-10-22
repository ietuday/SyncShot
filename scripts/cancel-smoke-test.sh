#!/usr/bin/env bash
set -euo pipefail

# This test launches the real CLI in a disposable workspace and interrupts it
# during image processing. It must not corrupt the previously published outputs.
ROOT="$(pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
go build -o "$TMP/syncshot" ./cmd/syncshot
cd "$TMP"
mkdir -p inputs/audio inputs/images output/video output/shorts
printf 'previous video' > output/video/final.mp4
printf 'previous shorts' > output/shorts/short_000.mp4

# Long input ensures the process is active when signalled.
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=180' -c:a libmp3lame inputs/audio/narration.mp3
for i in $(seq -w 1 12); do
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'testsrc2=size=1920x1080:rate=1' -frames:v 1 "inputs/images/$i.png"
done

"$TMP/syncshot" >run.log 2>&1 &
pid=$!
# Let real FFmpeg image conversion or rendering begin.
active=0
for i in $(seq 1 200); do
  if grep -Eq 'Processing images|Creating YouTube video|Creating Shorts' run.log; then
    active=1
    break
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    cat run.log
    echo 'SyncShot exited before interruption' >&2
    exit 1
  fi
  sleep 0.1
done
if [ "$active" -ne 1 ]; then echo 'pipeline never became active' >&2; kill "$pid"; wait "$pid" || :; exit 1; fi
kill -INT "$pid"
set +e
wait "$pid"
status=$?
set -e
test "$status" -ne 0 || { echo 'expected interrupted pipeline to fail' >&2; exit 1; }
test "$(cat output/video/final.mp4)" = 'previous video' || { echo 'existing video overwritten' >&2; exit 1; }
test "$(cat output/shorts/short_000.mp4)" = 'previous shorts' || { echo 'existing Shorts overwritten' >&2; exit 1; }
test ! -e output/.work.syncshot.lock || { echo 'lock was not released' >&2; exit 1; }
echo 'Full CLI cancellation smoke test passed.'

#!/usr/bin/env bash
set -euo pipefail

# Run in a temporary workspace: main.go uses relative input/output paths.
ROOT="$(pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

go build -o "$TMP/syncshot" ./cmd/syncshot
cd "$TMP"
mkdir -p inputs/audio inputs/images

ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=440:duration=3' -c:a libmp3lame inputs/audio/narration.mp3
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=blue:s=320x180' -frames:v 1 inputs/images/001.png
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=red:s=320x180' -frames:v 1 inputs/images/002.png

"$TMP/syncshot"

test -s output/video/final.mp4
test -s output/shorts/short_000.mp4

video_dims="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 output/video/final.mp4)"
short_dims="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 output/shorts/short_000.mp4)"
test "$video_dims" = "1920x1080" || { echo "Bad video dimensions: $video_dims"; exit 1; }
test "$short_dims" = "1080x1920" || { echo "Bad short dimensions: $short_dims"; exit 1; }

ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nw=1 output/video/final.mp4 | grep -q codec_name=aac
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nw=1 output/shorts/short_000.mp4 | grep -q codec_name=aac

duration="$(ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 output/video/final.mp4)"
awk -v d="$duration" 'BEGIN { if (d < 2.0 || d > 4.5) exit 1 }' || { echo "Unexpected duration: $duration"; exit 1; }

echo "Smoke test passed: final video and Shorts have correct dimensions, duration and audio."

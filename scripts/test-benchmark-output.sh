#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
verify() { bash "$ROOT/verify-benchmark-output.sh" "$1" "$2" "$TMP/duration.txt"; }
if verify "$TMP/missing.mp4" "" >/dev/null 2>&1; then echo "missing output accepted" >&2; exit 1; fi
printf 'garbage' > "$TMP/invalid.mp4"
if verify "$TMP/invalid.mp4" "" >/dev/null 2>&1; then echo "invalid output accepted" >&2; exit 1; fi
ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'color=c=blue:s=160x90:r=12:d=1' -c:v libx264 -pix_fmt yuv420p "$TMP/good.mp4"
old="$(stat -c '%d:%i:%s:%Y:%Z' "$TMP/good.mp4")"
if verify "$TMP/good.mp4" "$old" >/dev/null 2>&1; then echo "unchanged output accepted" >&2; exit 1; fi
size="$(verify "$TMP/good.mp4" "")"
test "$size" -gt 0
awk 'NR==1 {if ($1+0<0.8 || $1+0>1.2) exit 1}' "$TMP/duration.txt"
echo "Benchmark output validator tests passed"

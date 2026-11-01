#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
bash -n scripts/qualify-real-media-low-memory.sh
python3 - <<'PY'
from pathlib import Path
script=Path("scripts/qualify-real-media-low-memory.sh").read_text()
assert 'RUN_REPORT="$(mktemp -d "$REPORT_DIR/qualification-XXXXXXXX")"' in script
assert 'check-low-memory-benchmark.py "$RUN_REPORT"' in script
assert 'Report directory cannot be inside an input directory' in script
print("Real-media qualification isolation checks passed")
PY

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/audio" "$TMP/images"
# A nested report directory must be rejected before any report is created.
if bash scripts/qualify-real-media-low-memory.sh "$TMP/audio" "$TMP/images" "$TMP/audio/reports" >"$TMP/output.log" 2>&1; then
  echo "Expected nested report path to be rejected" >&2
  exit 1
fi
if [[ -e "$TMP/audio/reports" ]]; then
  echo "Invalid report directory was created inside source audio directory" >&2
  exit 1
fi
grep -q "Report directory cannot be inside an input directory" "$TMP/output.log"
echo "Real-media qualification input-safety tests passed."

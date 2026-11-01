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

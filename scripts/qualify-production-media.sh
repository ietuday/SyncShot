#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if (( $# != 3 )); then
  echo "Usage: $0 config.json output-video.mp4 report-directory" >&2
  exit 2
fi
CONFIG="$(realpath "$1")"
OUTPUT="$(realpath -m "$2")"
REPORT="$(realpath -m "$3")"
if [[ ! -f "$CONFIG" ]]; then
  echo "Configuration file not found: $CONFIG" >&2
  exit 2
fi
if [[ -z "${SYNC_SHOT_BENCHMARK_INPUTS:-}" ]]; then
  echo "Set SYNC_SHOT_BENCHMARK_INPUTS to all media and config paths" >&2
  exit 2
fi
if [[ -z "${SYNC_SHOT_BENCHMARK_WORKLOAD_ID:-}" || "${SYNC_SHOT_BENCHMARK_WORKLOAD_ID}" == "unlabeled" ]]; then
  echo "Set a stable, descriptive SYNC_SHOT_BENCHMARK_WORKLOAD_ID" >&2
  exit 2
fi
mkdir -p "$REPORT" "$(dirname "$OUTPUT")"
if [[ -e "$OUTPUT" ]]; then
  echo "Refusing to overwrite an existing qualification output: $OUTPUT" >&2
  exit 2
fi
# Preflight: validate source paths and CLI settings before starting an expensive render.
IFS=":" read -r -a INPUT_PATHS <<< "$SYNC_SHOT_BENCHMARK_INPUTS"
python3 scripts/fingerprint-inputs.py --output /dev/null "${INPUT_PATHS[@]}"
go run ./cmd/syncshot --config "$CONFIG" --output "$OUTPUT" --dry-run
RUN_REPORT="$(mktemp -d "$REPORT/qualification-XXXXXXXX")"
echo "Qualification evidence directory: $RUN_REPORT"

STAGE="benchmark"
write_status() {
  local code="$1"
  python3 - "$RUN_REPORT/status.json" "$STAGE" "$code" <<'PY'
import json,sys
from datetime import datetime,timezone
out,stage,code=sys.argv[1],sys.argv[2],int(sys.argv[3])
with open(out,"w",encoding="utf-8") as file:
    json.dump({"stage":stage,"exit_code":code,"status":"success" if code==0 else "failure","recorded_utc":datetime.now(timezone.utc).isoformat()},file,indent=2)
    file.write("\n")
PY
}
on_exit() {
  local code="$1"
  trap - EXIT
  write_status "$code" || true
  if (( code != 0 )); then
    echo "Qualification failed at '$STAGE' (exit $code). Evidence: $RUN_REPORT" >&2
  fi
}
trap 'on_exit "$?"' EXIT

SYNC_SHOT_BENCHMARK_OUTPUT="$OUTPUT" \
  bash scripts/benchmark-long-video.sh "$RUN_REPORT" --config "$CONFIG" --output "$OUTPUT" --timeout "${SYNC_SHOT_QUALIFICATION_TIMEOUT:-3h}"
STAGE="benchmark_summary"
python3 scripts/summarize-benchmarks.py "$RUN_REPORT" --json "$RUN_REPORT/qualification-summary.json"
STAGE="video_quality"
python3 scripts/check-media-quality.py "$OUTPUT" \
  --width "${SYNC_SHOT_EXPECT_WIDTH:-1920}" \
  --height "${SYNC_SHOT_EXPECT_HEIGHT:-1080}" \
  --min-duration "${SYNC_SHOT_MIN_DURATION:-30}" \
  --max-duration "${SYNC_SHOT_MAX_DURATION:-4000}" > "$RUN_REPORT/media-quality.json"
STAGE="audio_integrity"
python3 scripts/check-audio-integrity.py "$OUTPUT" > "$RUN_REPORT/audio-integrity.json"
STAGE="complete"
echo "Qualification checks passed. Review video manually and inspect reports in: $RUN_REPORT"

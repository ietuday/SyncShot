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
python3 scripts/check-qualification-paths.py "$OUTPUT" "$CONFIG" "$REPORT" "${INPUT_PATHS[@]}"
RUN_REPORT="$(mktemp -d "$REPORT/qualification-XXXXXXXX")"
echo "Qualification evidence directory: $RUN_REPORT"
STAGE="media_audit"
write_status() {
  python3 scripts/write-qualification-status.py "$RUN_REPORT/status.json" "$STAGE" "$1"
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
python3 scripts/audit-qualification-inputs.py "${INPUT_PATHS[@]}" --output "$RUN_REPORT/input-audit.json"
STAGE="media_decode"
python3 scripts/check-qualification-media-decode.py "${INPUT_PATHS[@]}" --timeout-per-file "${SYNC_SHOT_DECODE_TIMEOUT_PER_FILE:-120}" --output "$RUN_REPORT/media-decode.json"
STAGE="input_fingerprint"
python3 scripts/fingerprint-inputs.py --output "$RUN_REPORT/inputs-fingerprint.json" "${INPUT_PATHS[@]}"
STAGE="config_dry_run"
go run ./cmd/syncshot --config "$CONFIG" --output "$OUTPUT" --dry-run
STAGE="preflight_summary"
python3 scripts/summarize-qualification-preflight.py "$RUN_REPORT/input-audit.json" "$RUN_REPORT/media-decode.json" "$RUN_REPORT/inputs-fingerprint.json" --output "$RUN_REPORT/preflight-summary.json"

STAGE="benchmark"
write_status() {
  python3 scripts/write-qualification-status.py "$RUN_REPORT/status.json" "$STAGE" "$1"
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

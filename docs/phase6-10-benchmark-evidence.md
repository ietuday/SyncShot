# Phase 6.10 — CI benchmark evidence

The short (two-second) FFmpeg benchmark integration smoke test now optionally copies validated `summary.json`, `measurements.csv` and `process-memory.csv` to a configured evidence folder. The CI job uploads that folder as a GitHub Actions artifact retained for 14 days.

This enables auditing actual observed CI benchmark readings from the test run. These measurements reflect a tiny synthetic input and are NOT representative of production long-video performance; they should not be compared directly with 15/30/60-minute qualification runs. The script continues deleting its temporary media workspace after the run.

Local usage: `SYNC_SHOT_BENCHMARK_EVIDENCE_DIR=./benchmark-evidence bash scripts/test-benchmark-runner-e2e.sh`. Review artifacts before sharing because environment details can be present in summary JSON.

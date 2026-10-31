# Phase 6.3 — Benchmark regression comparison

Compare summaries from equivalent workloads (same narration, image set, FFmpeg version, hardware, resolution and chunk size):

    python3 scripts/compare-benchmarks.py baseline.json candidate.json --max-regression-percent 15

Inputs are one-run JSON arrays produced by `scripts/summarize-benchmarks.py`. The comparator reports percent change and exits nonzero when realtime factor, total sampled process-tree RSS or sampled FFmpeg RSS increases by more than the threshold. Lower is better for all three metrics. Run comparator on matching test conditions; comparisons across different video lengths or hardware are misleading.

The comparison tests run in CI, but real long-duration benchmark measurements are not included and performance gates are not enforced on PRs without representative baseline data. Zero and non-finite input metrics are rejected.

# Phase 6.4 — Benchmark workload labels

Set a stable workload ID before each benchmark. It should encode input media, resolution, chunk size, effects, FFmpeg version and machine class. For example:

    SYNC_SHOT_BENCHMARK_WORKLOAD_ID=narration15m-720p-chunk4-machineA bash scripts/benchmark-long-video.sh ./output/benchmarks --config ./config/long.json --chunk-scenes 4

Each run stores `workload-id.txt`; the aggregator includes `workload_id` in its JSON reports. The comparator rejects missing, unlabeled or mismatched workloads to prevent obvious apples-to-oranges results.

Labels are supplied by the operator and are **not** independently verified against inputs, hardware or configuration. Use identical labels only for truly comparable jobs. Prior summaries without labels must be rerun or labeled through a separately verified process before comparison. Real 15–60-minute results remain unmeasured.

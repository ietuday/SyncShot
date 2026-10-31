# Phase 6.2 — Parameterized Real-Video Benchmarks

The benchmark runner now accepts SyncShot CLI arguments **after** the benchmark output directory. It logs the fully shell-escaped invocation in each run's `command.txt` so that runs can be reproduced.

Examples:

    bash scripts/benchmark-long-video.sh ./output/benchmarks --config ./config/long-video.json --chunk-scenes 4 --timeout 3h

    SYNC_SHOT_BENCHMARK_OUTPUT=./output/video/custom.mp4 bash scripts/benchmark-long-video.sh ./output/benchmarks --config ./config/long-video.json --output ./output/video/custom.mp4 --chunk-scenes 8

The first argument always names the report folder. Omit it or use `./output/benchmarks` when running with defaults. The runner uses the Go binary built from the current branch and records environment versions and observed process memory. The `SYNC_SHOT_BENCHMARK_OUTPUT` value must match any non-default `--output` argument or output path specified in a JSON configuration.

For meaningful results, supply actual narration (15/30/60 min), source images, optional music and subtitles. Repeat tests with different chunk sizes under controlled system load and compare using:

    python3 scripts/summarize-benchmarks.py ./output/benchmarks --json ./output/benchmarks/summary.json

This change enables manual representative benchmarks. It **does not** include sample source media or claim measured performance improvements. Be mindful that `command.txt` can include local paths, so do not upload raw reports without reviewing their contents.

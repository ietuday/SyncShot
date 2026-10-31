# Phase 6.6 — Benchmark Input Fingerprints

To record deterministic SHA-256 fingerprints for selected benchmark media and config files, use `SYNC_SHOT_BENCHMARK_INPUTS` as a colon-delimited list of paths:

    SYNC_SHOT_BENCHMARK_WORKLOAD_ID=15m-720p-chunk4 \
    SYNC_SHOT_BENCHMARK_INPUTS='./inputs/audio:./inputs/images:./config/long-video.json' \
    bash scripts/benchmark-long-video.sh ./output/benchmarks --config ./config/long-video.json --chunk-scenes 4

The runner hashes each selected file and records a combined fingerprint in `inputs-fingerprint.json`. The summary exposes `input_fingerprint`. When *both* comparison reports contain fingerprints and they differ, the comparison refuses the workload.

**Limitations:** Input selection is operator-supplied and can omit important files. Missing or inaccessible paths fail the benchmark. Directories are recursively hashed, which adds CPU and I/O cost for large media libraries. Colons inside paths cannot be expressed in the environment variable. Filenames and paths can contain private information; inspect artifacts before sharing. Older reports use `unknown` and are still comparable with matching workload labels; therefore fingerprint checks are not mandatory for all comparisons. This is a reproducibility tool, not a claim of measured rendering performance.

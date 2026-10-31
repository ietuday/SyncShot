# Phase 6.5 — Automatic Benchmark Metadata

The Linux benchmark runner records Git commit, kernel/platform, logical CPU count, and FFmpeg/FFprobe/Go versions alongside sampled render metrics. Benchmark summary JSON now includes `source_commit`, `machine`, and `environment` alongside the operator-supplied `workload_id`.

Use `bash scripts/benchmark-long-video.sh ./output/benchmarks --config ./your.json` and `python3 scripts/summarize-benchmarks.py ./output/benchmarks`.

These are observability fields, not proof of workload equivalence. The benchmark comparator still requires matching workload IDs; hardware, settings and inputs must be checked by the operator. Existing reports without metadata remain readable with an `unknown` fallback. No long-form 15/30/60-minute benchmark is claimed as executed.

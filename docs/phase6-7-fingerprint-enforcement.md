# Phase 6.7 — Mandatory fingerprint verification

Performance comparisons now require both summary files to contain matching, valid lowercase SHA-256 `input_fingerprint` values (64 hex digits), plus matching non-default workload IDs. Missing or `unknown` fingerprints cause an error rather than silently allowing a potentially invalid comparison.

Capture media fingerprints with `SYNC_SHOT_BENCHMARK_INPUTS` on **both** benchmark runs. Include all narration, image, config, subtitle and music files used. Fingerprint collection remains opt-in at render time, but is required before running the comparator.

The tool does not automatically prove identical CPU, memory, FFmpeg binary or render settings; inspect metadata manually. It also cannot guarantee that operator-selected files cover the complete workload. Actual 15–60-minute performance numbers are still pending.

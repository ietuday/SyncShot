# Phase 6.1 Performance Qualification

Run representative 15-, 30-, and 60-minute narration workloads at 720p and 1080p, with chunk sizes 2, 4, and 8. Run each under comparable machine conditions and inspect transitions, narration timing, subtitles and Shorts.

Collect measurements with `bash scripts/benchmark-long-video.sh` and aggregate with `python3 scripts/summarize-benchmarks.py ./output/benchmarks --json ./output/benchmarks/summary.json`.

The summary rejects unsuccessful runs, missing media duration and invalid result files. It reports elapsed time, realtime factor, sampled RSS and output size. Linux /proc sampling is approximate. Full-length production benchmarks and manual playback checks have not been run by this PR.

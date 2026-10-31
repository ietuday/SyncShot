# Phase 5.7 — Resource-aware long-video benchmarks

Run a real SyncShot render using the existing configuration and inputs:

    bash scripts/benchmark-long-video.sh

The script compiles the CLI, executes it, and samples the Go parent plus recursive child process tree once per second on **Linux**. It saves a per-sample CSV (`process-memory.csv`), a summary (`measurements.csv`), tool versions, and render logs under `output/benchmarks/<UTC timestamp>`.

## Measurements

- **peak_process_tree_rss_kb**: maximum observed sum of resident memory of sampled descendants plus parent.
- **peak_ffmpeg_rss_kb**: maximum observed sum of sampled processes whose Linux `/proc/<pid>/comm` is `ffmpeg`.
- **elapsed_seconds** and **exit_code**: end-to-end wall time and status.
- **output_bytes**: final video file size when present.

These RSS readings are **sample-based approximations**, not kernel-enforced peak allocations; short-lived processes can be missed, and shared pages can be counted more than once. The script requires Linux `/proc`, `pgrep`, `awk`, `date`, `ffmpeg`, `go`, and other standard CLI tools. It does not measure GPU memory, Shorts disk peak, or guaranteed container memory usage. Run only one benchmark per workspace and ensure ample free disk space.

## Suggested acceptance matrix

Use the same source media, CPU resources and settings for comparable runs:

| Narration | Profile | Chunk sizes | Effects |
|---|---|---|---|
| 15 min | 720p / 1080p | 2 / 4 / 8 | Music + ducking + subtitles |
| 30 min | 720p / 1080p | 2 / 4 / 8 | Music + ducking + subtitles |
| 60 min | 720p / 1080p | 2 / 4 / 8 | Music + ducking + subtitles |

Also manually verify audio synchronization, subtitle timing, fade boundaries, video/Shorts publication, and cancellation recovery. No long-duration benchmarks are executed or claimed by this PR; local representative media and adequate machine capacity are required.

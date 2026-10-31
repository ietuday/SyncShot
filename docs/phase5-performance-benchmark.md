# Phase 5.3 — Long-video performance

## Optimization

Chunked-effects rendering now uses video-only intermediate chunks. Previously, each chunk decoded and trimmed narration to a temporary PCM WAV and re-encoded it into the intermediate MP4, even though the final mix already reads original narration. The new path avoids those redundant audio operations and intermediate WAV storage. Global music, ducking, subtitles and overlays are preserved by the existing final composition pass.

Existing full-effects integration tests and new video-only chunk tests cover regression behavior.

## Benchmark procedure

From the repository root, with representative inputs and settings configured in cmd/syncshot/main.go:

    bash scripts/benchmark-long-video.sh

The script writes elapsed seconds, process peak RSS, exit code, output size, logs and tool versions to output/benchmarks/<timestamp>. IMPORTANT: GNU time's RSS describes the Go parent, not the FFmpeg child processes; use pidstat or cgroup memory counters for accurate aggregate memory. Video size is collected only when final.mp4 is published.

For valid before/after measurements, compare the same 15-, 30- and 60-minute media, profile (720p/1080p), FPS, scene count, and chunk sizes (2/4/8). Also inspect audio/video duration drift and seam quality manually. This PR has not executed those long-duration benchmarks; no numerical speedup or memory improvement is claimed.

## Remaining bottlenecks

The final xfade graph still grows with the number of chunks, and video is encoded twice. Future steps: hierarchical joins, zero-fade stream-copy alternatives, encode-preset benchmarks, disk preflight and resumable work segments.

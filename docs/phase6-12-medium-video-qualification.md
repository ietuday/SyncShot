# Phase 6.12 — Medium Video Qualification

Run the manually triggered GitHub Actions `Medium video qualification` workflow with a duration from 10 to 600 seconds (default 60). It generates synthetic narration/images, renders a 720p chunked video, validates codec/audio/resolution/duration, and uploads a summary and media-quality report as CI artifacts.

Local run: `SYNC_SHOT_QUALIFICATION_SECONDS=60 bash scripts/test-medium-video-qualification.sh` (requires Go, Python 3, FFmpeg and FFprobe). Benchmark-run reports are temporary unless `SYNC_SHOT_BENCHMARK_EVIDENCE_DIR` is set. The normal pull-request CI checks shell syntax only; it does not automatically execute the manual medium-video workflow.

This is intermediate qualification, not a substitute for 15/30/60-minute real workload benchmarks and subjective playback validation. GitHub Actions may have resource and runtime constraints; manual duration inputs are bounded to 10–600 seconds.

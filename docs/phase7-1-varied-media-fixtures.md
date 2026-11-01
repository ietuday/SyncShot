# Phase 7.1 — Varied synthetic media fixture qualification

A new opt-in and PR-triggered workflow renders approximately 18 seconds of video using three different 1280×720 generated patterns (`testsrc2`, SMPTE bars and Mandelbrot) rather than only two flat-color stills, plus a generated 330 Hz audio tone. It tests basic input variation, benchmark execution, FFprobe media checks and evidence uploading.

This is **not** a representative real-world media benchmark: generated patterns and tones are synthetic, and subtitle, narration intelligibility, music, ducking, overlays, Shorts, timing perception and visual quality still require real-user-fixture or manually reviewed tests. The workflow provides a reproducible starting point without bundling copyrighted files or personal recordings.

Run locally with `bash scripts/test-varied-media-fixtures.sh` (requires Go, Python 3 and FFmpeg/FFprobe). Set `SYNC_SHOT_BENCHMARK_EVIDENCE_DIR` to persist summary and quality report.

# Phase 6.9 — End-to-end benchmark smoke test

A GitHub Actions `benchmark` job builds a **real** two-second synthetic narration and two images, renders a 720p video using the benchmark runner, verifies its published output, and generates a strict summary including duration and input fingerprint.

Run locally with `bash scripts/test-benchmark-runner-e2e.sh`. This requires Go, FFmpeg, FFprobe, Python 3 and Linux process inspection tools. Everything runs in a temporary directory and is cleaned up afterwards.

The test demonstrates the benchmark pipeline end-to-end but **does not validate long-video performance**. Real 15/30/60-minute production workloads are still needed for memory, runtime and playback qualification.

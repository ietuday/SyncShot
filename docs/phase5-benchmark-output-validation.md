# Phase 5.9 — Benchmark output verification

The benchmark now validates the produced video using `ffprobe` and checks that its output-file metadata changed from the state before the run. A missing, empty, unchanged or unprobeable output makes the benchmark fail instead of claiming successful output bytes.

To benchmark a custom output path (the CLI configuration must publish to the same path):

    SYNC_SHOT_BENCHMARK_OUTPUT=./output/video/custom.mp4 bash scripts/benchmark-long-video.sh

The default output path remains `./output/video/final.mp4`. A successful output duration is captured in `output-duration.txt` inside the benchmark directory.

**Limitations:** File metadata comparison is a heuristic, not a content hash or cryptographic proof that the renderer produced a different video; rerenders with identical media can still produce different metadata, and an external process can modify files. The benchmark requires `ffprobe` on the runner. It does not independently measure full 15/30/60-minute renders or validate subjective playback quality.

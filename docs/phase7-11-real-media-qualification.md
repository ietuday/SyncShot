# Phase 7.11 — Real-input production qualification

The `scripts/qualify-production-media.sh` entry point makes it easier to evaluate a *user-supplied* workload. It runs a fresh video render, then checks output H.264/AAC codecs, dimensions, expected duration, decodable non-silent audio, and writes a benchmark summary to a report folder. Inputs must be labeled and fingerprinted for meaningful future comparison.

Example:

```bash
SYNC_SHOT_BENCHMARK_WORKLOAD_ID='real-inputs-15m-1080p-machineA-v1' \
SYNC_SHOT_BENCHMARK_INPUTS='./inputs/audio:./inputs/images:./config.json' \
SYNC_SHOT_MIN_DURATION=870 SYNC_SHOT_MAX_DURATION=930 \
bash scripts/qualify-production-media.sh ./config.json ./output/video/qualification.mp4 ./output/real-media-reports
```

Use a **new output pathname**. The script refuses to overwrite an existing output. The `--output` option makes the output location explicit. Change expected dimensions with `SYNC_SHOT_EXPECT_WIDTH` and `SYNC_SHOT_EXPECT_HEIGHT` when rendering 720p (1280×720). By default these checks expect 1920×1080 and 30–4000 seconds. `SYNC_SHOT_QUALIFICATION_TIMEOUT` defaults to 3h.

**Still required:** manually review the complete rendered video and generated Shorts for visual crop, subtitle appearance/timing, narration clarity, music level, and sync. These checks do not measure subjective content quality or compare speed against a baseline automatically.

**Privacy:** report folders can capture filenames, environment details, and execution logs; review before sharing. The script runs only with user-supplied media on a machine where that media exists. It is not executed in GitHub CI because private production inputs are not available there.

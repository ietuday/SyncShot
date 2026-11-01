# SyncShot-Go

Put audio in inputs/audio and images in inputs/images
Run: go run ./cmd/syncshot

## Memory-conscious rendering (Phase 8.0)

The normal workflow is unchanged: put narration in `inputs/audio/`, put photos in `inputs/images/`, then run `go run ./cmd/syncshot`. Automatic cinematic scenes now render in **two-scene chunks by default**, with **two parallel image-processing workers** (previously the default rendered the full timeline in one FFmpeg graph and used four image workers). This aims to reduce peak memory on laptops such as 12 GiB Ubuntu machines.

For lower memory pressure, run `go run ./cmd/syncshot --chunk-scenes 1`. To explicitly restore the old unchunked cinematic path, use `--chunk-scenes 0`. Both `CinematicChunkScenes` and `MaxWorkers` remain configurable via JSON.

**Validation:** run `go test ./...` and retry your actual 15-minute narration with 10 images. The change does not yet prove that all long media jobs fit in 12 GiB RAM; monitor `free -h` and kernel OOM messages. Explicit cinematic timelines still use their separate renderer, and are not affected by this default.

## Diagnosing FFmpeg SIGKILL (Phase 8.1)

If FFmpeg exits with `signal: killed`, SyncShot prints an actionable hint. On Linux this can indicate the kernel OOM killer, but it can also mean another process sent SIGKILL. Confirm with `sudo journalctl -k | grep -iE 'out of memory|oom|killed process'`; monitor available memory with `free -h`. To reduce the number of active cinematic scenes, retry `go run ./cmd/syncshot --chunk-scenes 1`. The diagnostic does not yet prevent OOM or automatically retry a killed render.

## Phase 8.2 — Automatic low-memory mode

The CLI now accepts `--memory-mode auto|low|normal` (default: `auto`). On Linux hosts reporting **16 GiB or less total physical RAM** via `/proc/meminfo`, automatic cinematic rendering selects a lower-memory preset: **720p**, **one scene per chunk**, and **one image-processing worker**, unless those values have been customized. On other systems the existing 1080p, two-scene defaults remain. An explicit JSON `RenderProfile` is preserved; explicitly configured nondefault chunk/worker values are also preserved. An explicit command-line `--chunk-scenes` overrides automatic selection.

To force the lower-memory preset: `go run ./cmd/syncshot --memory-mode low`. To retain normal defaults on a low-RAM Linux host: `go run ./cmd/syncshot --memory-mode normal`.

This is a conservative host-RAM heuristic, not real-time available-memory monitoring or an OOM guarantee. Test a representative long-form render while checking `free -h` and kernel OOM logs.

## Phase 8.3 — Reuse completed cinematic chunks after interrupted runs

Automatic chunked cinematic rendering saves each **finished visual chunk** in `output/video/.syncshot-chunk-cache/` (relative to the configured output directory). A new run checks cached MP4s using SHA-256 identities of the processed image **contents**, scene motion/duration, resolution, FPS, crossfade and a cache format version. Existing media is also checked for nonzero size and expected duration before reuse. This avoids re-rendering finished visual chunks after a failed or interrupted run. Incomplete chunks are written to temporary paths and never published as complete. Final narration, optional music/subtitles/graphics, and final publication are recomputed on each run.

Cache files consume disk space and are **not automatically purged** in this phase. To reclaim storage, remove `output/video/.syncshot-chunk-cache/` while SyncShot is stopped. A cache hit saves rendering time, but does not recover a partially rendered scene or solve FFmpeg OOM during the final stitching pass. Run `go test ./internal/cinematic` and test a real interrupted long-form render before relying on recovery.

## Phase 8.4 — Repeatable 15-minute low-memory qualification

Run `bash scripts/qualify-low-memory-15m.sh` from the project root to generate a **synthetic** 925.36-second AAC narration and 10 still images, then render through the production CLI at 720p, 24 FPS, 1 scene per chunk and 1 image worker. This is a lengthy, resource-intensive **manual** test and does not run in ordinary PR CI. Its benchmark output includes process/FFmpeg peak RSS, elapsed time and logs beneath `output/qualification-15m/run-*/`. The script checks final video resolution, audio presence and runtime, and returns a failure on render/quality errors. It deletes its temporary generated media/video after the test; benchmark measurements remain.

For the **real** narration/image collection, use the existing `scripts/qualify-production-media.sh` with explicitly supplied input/config paths and `SYNC_SHOT_EXPECT_WIDTH=1280` / `SYNC_SHOT_EXPECT_HEIGHT=720` in the environment. Those media-specific results are still needed to validate the user's observed FFmpeg OOM failure; a synthetic successful render alone does not establish reliability for all workloads.

## Phase 8.5 — Automatic chunk-cache housekeeping

After **successful** cinematic final-video publication, SyncShot removes cache files that are older than seven days **and not referenced by the current render**. Only regular, hash-named MP4 entries inside the dedicated `.syncshot-chunk-cache` directory are eligible. Fresh chunks, active chunks, symlinks and unrelated files are preserved. If the render fails, cleanup is skipped so completed chunks remain available for recovery. Cleanup errors are logged as warnings rather than invalidating a successfully published video. Disk usage can still grow between successful runs, and disk-space monitoring is a future improvement.

## Phase 8.6 — Disk-space preflight

Before rendering starts, SyncShot checks free filesystem space in both the work directory and final-video output directory on Linux. When either has less than **2 GiB free**, rendering stops early with an actionable error rather than consuming more storage and failing halfway through. On non-Linux platforms this check is currently skipped. This is a conservative minimum, not a forecast of total disk consumption for an unusually long render; check available storage before multi-hour jobs. The normal audio + images command is unchanged.

## Phase 8.7 — Bounded final-stitch filter threading

The automatic chunked-effects final FFmpeg stitching pass now sets `-filter_complex_threads 1` and `-filter_threads 1` to reduce concurrency and potential peak RAM use for multi-chunk crossfades. Rendering may be slower on high-core hosts. This change does not guarantee OOM-free rendering; benchmark its impact using `bash scripts/qualify-low-memory-15m.sh` and inspect peak FFmpeg RSS in `measurements.csv`.

## Phase 8.8 — Low-memory regression and A/V endpoint validation

The manual `bash scripts/qualify-low-memory-15m.sh` now rejects a render whose recorded peak FFmpeg RSS exceeds `SYNC_SHOT_MAX_FFMPEG_RSS_MIB` (default 8192 MiB). It also checks decoded audio/video stream start and end timestamps are within 0.5 seconds using ffprobe; this **does not** validate word-level lip sync or perceptual synchronization. The limit is a test threshold, not a runtime memory cap, and can be adjusted for differently sized test machines. The actual 15-minute user media still needs a separate manual test on the 12 GiB Ubuntu host.

## Phase 8.9 — Failed-render diagnostics

The long-video benchmark harness writes `failure-diagnostics.json` beside `run.log` and `measurements.csv` after an unsuccessful run. The JSON distinguishes an FFmpeg `signal: killed` from an actual kernel OOM confirmation: the latter requires kernel logs (for example `sudo journalctl -k`) and is **not** inferred from SIGKILL alone. The summary provides the exact low-memory retry suggestion. Run unit checks with `python3 scripts/test-summarize-render-failure.py`.

## Phase 8.10 — Interrupted publication recovery validation

The cinematic integration suite now injects a final-publication failure after visual chunks have rendered, verifies no final output is published, and retries the same render. The second attempt must reuse unchanged cached chunks and produce a playable video of the expected duration. Run `go test ./internal/cinematic -run TestInterruptedPublishPreservesCacheForRetry -count=1` (requires FFmpeg and ffprobe). This simulates a publisher failure, not a real OOM or a forcibly terminated OS process. The original 15-minute narration still needs validation on the 12 GiB laptop.

## Phase 8.11 — Corrupt cached chunk recovery test

An FFmpeg integration test deliberately corrupts a completed content-addressed visual MP4 cache entry and repeats the cinematic render. The renderer must reject the invalid cached media, rebuild it, and publish a valid final video. This validates corrupted-cache recovery without relying on manually deleting old chunks. Run `go test ./internal/cinematic -run TestCorruptCachedChunkIsRebuilt -count=1` with FFmpeg installed. The original 15-minute laptop rendering benchmark still requires manual execution.

## Phase 8.12 — Test real audio and images on the 12 GiB laptop

After pulling `syncshot-go`, run `bash scripts/qualify-real-media-low-memory.sh inputs/audio inputs/images`. This manually benchmarks the actual source files with the conservative 720p / one-scene-chunk / one-worker preset and checks peak FFmpeg RSS (default ceiling 8192 MiB), video dimensions, and stream start/end alignment. Benchmark logs and measurements remain in `output/real-media-qualification/run-*/`; the temporary qualification video is removed after the test. Your input files are never altered. This test can take substantial CPU time and storage and does not run in ordinary PR CI. A successful run on your 12 GiB system is still required before claiming the original OOM is fixed.

## Phase 8.13 — Isolated real-media qualification reports

Each real-media qualification now creates a unique `output/real-media-qualification/qualification-*/` report root, so the memory gate reads the current benchmark rather than a potentially newer/older unrelated run. It rejects report directories nested inside the source audio or image directories to prevent the test from scanning its own outputs. Source media is still not modified. Run `bash scripts/test-real-media-qualification.sh` for basic harness wiring checks.

## Phase 8.14 — Qualification preflight safety

The manual real-media qualification runner now resolves and verifies audio/image source directories, rejects report directories nested inside them **before creating any files**, and checks for required Go/FFmpeg/ffprobe/Python commands before starting. Run `bash scripts/test-real-media-qualification.sh` to verify nested-path rejection creates no report directory. Real 15-minute rendering on the user's laptop remains unverified.

## Phase 8.15 — Consolidated real-media qualification summary

The manual real-media qualification generates `summary.json` and `summary.md` inside the current `qualification-*` report directory, reporting benchmark exit status, elapsed time, peak FFmpeg/process-tree RSS and output size. Run `python3 scripts/test-summarize-real-media-qualification.py` for summary regression checks. The summary records rendering benchmark metrics; passing memory, audio/video alignment and output dimensions are checked separately by the qualification command. No actual user-laptop render has been performed by this change.

## Phase 8.16 — Keep diagnostic reports for failed qualification

The real-media qualification runner now attempts to write `summary.json` and `summary.md` when it exits unsuccessfully after the benchmark starts, without concealing the original exit status. It prints the specific qualification report directory to stderr on failure and still removes temporary rendered media. If the underlying benchmark did not produce `measurements.csv` (for example failure before recording began), its summary may not be available, but existing logs are preserved. The original 15-minute media still requires a manual Ubuntu qualification run.

## Phase 8.17 — Qualification failure classification

If the real-media qualification fails after the benchmark report directory is created, it now saves `failure-analysis.json` with the failing stage (`benchmark`, `memory`, `av_sync`, or `dimensions`), exit code, and troubleshooting advice. `ffmpeg_sigkill` is not treated as confirmed OOM; use the Linux kernel journal for confirmation. Run `python3 scripts/test-analyze-qualification-failure.py` for the classifier regression tests. Original 15-minute workload validation on the user's 12 GiB laptop is still pending.

## Phase 8.18 — Actionable qualification summaries

Real-media `summary.json` and `summary.md` now include suggested next steps based on recorded render status and peak FFmpeg RSS. A failed render points to logs and OOM confirmation; high measured RAM encourages workload reduction; a missing RSS sample triggers instrumentation review. These are evidence-based suggestions, not guarantees of rendering success, and the actual 15-minute media still needs a local test.

## Phase 8.19 — Memory qualification evidence guardrails

The RSS qualification check now requires exactly one benchmark `measurements.csv` under the chosen report directory and rejects missing or zero peak FFmpeg memory samples. Ambiguous report directories no longer silently use the most recently modified run. Nonfinite RSS limits are also rejected. Run `python3 scripts/test-check-low-memory-benchmark.py` for focused regression tests. This does not itself benchmark the original 15-minute media.

## Phase 8.20 — End-to-end qualification smoke in CI

`bash scripts/smoke-qualify-real-media.sh` builds short synthetic input media and invokes the **same** manual real-media qualification wrapper used for the 15-minute laptop workload. It asserts successful rendering/qualification, a nonzero FFmpeg RSS sample, a single summary and unmodified source media. The dedicated GitHub Actions workflow runs this short smoke test on relevant pull request changes. It is not a substitute for rendering actual 15-minute media on the user's 12 GiB Ubuntu laptop.

## Phase 8.21 — Keep qualified video for manual inspection

By default the real-media qualification deletes its temporary rendered video after checks complete. Set `SYNC_SHOT_KEEP_QUALIFIED_VIDEO=1 bash scripts/qualify-real-media-low-memory.sh inputs/audio inputs/images` to retain a successfully qualified `qualified.mp4` in that run's `qualification-*/` report folder for visual and audio review. Source narration and images remain untouched. Retaining long video consumes additional disk space; failed or unvalidated outputs are not retained. The end-to-end qualification smoke test exercises this opt-in mode.

## Phase 8.22 — Final real-media qualification verdict

After qualification exits, `qualification-status.json` records `status`, `exit_code`, and `last_stage`, including whether optional video retention failed after rendering passed. This final verdict is distinct from `summary.json`, which records the rendering benchmark alone. The end-to-end smoke test checks the final verdict after retaining its synthetic video. The original 15-minute media has not yet been tested on the 12 GiB Ubuntu laptop.

## Phase 8.23 — Qualification failure-path CI regression

The real-media qualification GitHub Actions smoke workflow now also runs `bash scripts/smoke-qualification-failure.sh`, which deliberately sets an unrealistically low FFmpeg RSS budget on a short synthetic render. It asserts the validation fails with a nonzero exit, preserves `summary.json`, records `qualification-status.json` with a failed memory stage, writes `failure-analysis.json`, and does not retain an unqualified video. This tests report correctness on failure; the original 15-minute laptop render remains unverified.

## Phase 8.24 — Invalid-media qualification regression

The qualification failure-path smoke now also supplies a corrupt narration file alongside an otherwise valid image. It asserts the wrapper fails rather than reporting success or retaining a `qualified.mp4`. This is in addition to the existing post-render memory-budget failure test. Run `bash scripts/smoke-qualification-failure.sh`. The original 15-minute workload on a 12 GiB Ubuntu laptop remains unverified.

## Phase 8.25 — Original-media readiness preflight

Before a potentially lengthy real-media qualification run, `scripts/preflight-real-media.py` checks that supported narration and image files exist and are readable by ffprobe, lists narration durations, and requires at least 2 GiB of free space in the chosen report directory. Run `bash scripts/qualify-real-media-low-memory.sh inputs/audio inputs/images` as usual; the preflight runs automatically. It does not guarantee memory safety or replace the manual 15-minute test on the 12 GiB laptop.

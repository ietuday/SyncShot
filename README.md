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

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

## Phase 8.26 — Strict media preflight regression checks

Preflight now rejects zero/malformed image dimensions, nonfinite narration durations and invalid free-disk thresholds. The dedicated qualification GitHub Actions workflow runs `python3 scripts/test-preflight-real-media.py` alongside its end-to-end smoke tests. The real 15-minute narration with 10 images on the 12 GiB Ubuntu laptop still requires a manual test.

## Phase 8.27 — Narration audio-stream validation

Real-media preflight now requires each supported narration file to contain an actual readable audio stream, not merely a positive container duration. This prevents a mislabeled silent video container from passing the input check. The qualification CI's Python preflight regression tests cover a missing audio stream. Run `python3 scripts/test-preflight-real-media.py` for focused tests. The original 15-minute render on the 12 GiB laptop remains unverified.

## Phase 8.28 — Preflight rejection regression coverage

The dedicated real-media qualification CI's Python tests now additionally cover absent narration/images, unreadable ffprobe media and insufficient available disk. These checks fail before launching an expensive render. Run `python3 scripts/test-preflight-real-media.py`. The original 15-minute user workload on the 12 GiB Ubuntu laptop is still unverified.

## Phase 8.29 — Host RAM and swap evidence for long rendering

The benchmark now records `host-memory-before.txt` and `host-memory-after.txt` with `/proc/meminfo` values (MemTotal, MemAvailable, SwapTotal and SwapFree), where available. These snapshots help interpret FFmpeg process RSS relative to the machine's available memory and swap, but do not prove a kernel OOM event. To confirm an OOM SIGKILL, inspect `sudo journalctl -k` on the device. The original 15-minute render on the 12 GiB laptop remains outstanding.

## Phase 8.30 — Share a compact qualification diagnostic bundle

After the manual 15-minute qualification finishes (or fails), select the resulting `output/real-media-qualification/qualification-XXXXXXXX` directory and run `python3 scripts/package-qualification-report.py output/real-media-qualification/qualification-XXXXXXXX --output output/real-media-diagnostics.tar.gz`. The resulting archive contains only summary/status JSON, Markdown, measurement CSV and selected system-memory/failure diagnostics, **not** your narration, images, rendered video, binaries or raw run logs. Review the archive before sharing: summaries and measurements may still expose workload details. This provides inspectable evidence from the real laptop without uploading private media. Run `python3 scripts/test-package-qualification-report.py` for regression checks.

## Phase 8.31 — Diagnostic bundle publication safety

Diagnostic archive exports now refuse to overwrite existing archives, create output via a temporary archive followed by an atomic no-replace link, reject symlinked run directories, and reject output paths inside the qualification folder. Run `python3 scripts/test-package-qualification-report.py` to exercise the safeguards. Reports can still reveal workload information; inspect before sharing. Original 15-minute render on the 12 GiB laptop remains unverified.

## Phase 8.33 — Bounded qualification diagnostic bundles

The diagnostic packager now rejects any whitelisted input over 16 MiB or a combined uncompressed input size over 32 MiB. This avoids unexpectedly large archives or memory/disk pressure from corrupted measurement and summary files. An oversize failure removes the temporary archive without publishing the destination. Empty regular diagnostic files remain supported. Run `python3 scripts/test-package-qualification-report.py` for regression coverage. These limits do not replace the manual 15-minute qualification on the 12 GiB laptop.

## Phase 9.1 — Narration-guided scene planning foundation

The new `go run ./cmd/storyplan` command converts **existing timestamped transcription data** into a structured JSON scene manifest. It does **not** transcribe audio, synthesize visuals, animate characters or render the scene manifest yet. Those are separate planned integrations. Styles: `mythological_3d` (default), `cartoon_2d`, `cinematic_realistic`.

Save an input file `transcript.json`:

```json
{
  "audio": "inputs/audio/narration.m4a",
  "duration_seconds": 12,
  "segments": [
    {"start": 0, "end": 6, "text": "Shri Ram walks through the forest."},
    {"start": 6, "end": 12, "text": "He meets a sage."}
  ]
}
```

Then run:

```bash
go run ./cmd/storyplan --transcript transcript.json --output scene-plan.json --style mythological_3d --scene-seconds 6
go test ./internal/storyplan ./cmd/storyplan
```

The output contains time-aligned scene boundaries and draft visual prompts for manual review or future animation providers. Longer transcript segments are split into equal-duration scenes, repeating their narration text rather than inventing word-level timing. No transcription service is configured. Use an external transcription tool to supply timestamped transcript JSON, and review all generated prompts for story accuracy before using them in an animation pipeline.

## Phase 9.2 — Optional local Hindi/English audio transcription

To generate the timestamped JSON required by Phase 9.1, install `faster-whisper` in a Python virtual environment (optional dependency):

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install faster-whisper
python3 scripts/transcribe-audio.py --audio inputs/audio/narration.m4a --output transcript.json --language hi --model tiny
go run ./cmd/storyplan --transcript transcript.json --output scene-plan.json --style mythological_3d --scene-seconds 8
```

The transcription script runs on **CPU using int8 inference**, two threads and one worker by default, with the lightweight `tiny` model (optional `base` and `small`). This is intended to make transcription approachable on a 12 GiB laptop but is **not a measured RAM guarantee**. The initial model download requires internet access and may be blocked by corporate proxies; use an appropriately cached model where available. Hindi speech can need a larger model and manual proofreading for accuracy. No user audio is uploaded by this script's inference pipeline, although model installation/download involves external repositories.

Output is a JSON transcript with `audio`, `duration_seconds`, and timestamped `segments`, compatible with Phase 9.1. The script refuses to overwrite an existing output file. The timestamped transcript is not yet hooked automatically into the primary `syncshot` renderer; it produces **scene prompts, not animated video**. Run `python3 scripts/test-transcribe-audio.py` for offline unit tests without downloading a model.

## Phase 9.3 — Optional AI scene illustrations

This phase adds a **separate** script to create PNG illustrations from the Phase 9.1 scene plan. It does not yet animate the illustrations or integrate them with the final MP4 renderer. The script previews five scenes by default, performs **no paid requests unless `--execute` is supplied**, and refuses to overwrite existing scene image files. Each generation request is billed by the API provider; generating 100+ scenes can be expensive. Review visual prompts before executing.

```bash
python3 scripts/generate-scene-images.py --plan scene-plan.json --output-dir output/scene-images --limit 5
export OPENAI_API_KEY='YOUR_KEY' # use a secure environment injection, never commit credentials
python3 scripts/generate-scene-images.py --plan scene-plan.json --output-dir output/scene-images --limit 5 --execute
```

The `--execute` mode requires network access to OpenAI's Images API, an authorized API key, and appropriate billing. It requests one 1024x1024 PNG per scene with the `gpt-image-1` model. Images may not maintain character identity across independent calls; character consistency and real image-to-video animation are future phases. Run `python3 scripts/test-generate-scene-images.py` to test locally without network access or API charges.

## Phase 9.4 — Runway image-to-video task submission (optional)

Generate real animated video clips from scene images using the Runway API. This is **not local FFmpeg zoom/pan**: it submits image-to-video generation tasks to Runway's Gen-4 Turbo model. This first adapter submits tasks and stores task IDs; it does not yet poll, download, stitch or synchronize completed clips, or upload local PNGs. You must provide HTTPS-hosted images; avoid publishing private media publicly.

Create `scene-image-urls.json` mapping scene numbers to approved HTTPS image URLs, e.g. `{"1":"https://example.com/scene1.png"}`. First preview one task without charges:

```bash
python3 scripts/animate-scene-images.py --plan scene-plan.json --image-urls scene-image-urls.json --output preview-animation.json --limit 1
```

To **explicitly submit paid generation tasks**, install `runwayml`, set `RUNWAYML_API_SECRET` securely, choose a **different** output filename, and add `--execute`. Verify provider pricing, credits and eligibility before doing so. The default clip duration is 5 seconds. Do not commit secrets or user media. The output contains task IDs only; a future stage must download results and align scenes to narration.

## Phase 9.5 — Check and download completed animation tasks

Use the Phase 9.4 `--execute` task manifest to inspect Runway generation status. This step does not create new paid generations. Running it requires `RUNWAYML_API_SECRET`, the optional `runwayml` Python package and network access. By default it **only checks task status** and writes a new JSON report; add `--download` to save successful MP4 clips.

```bash
python3 scripts/retrieve-animation-clips.py --tasks submitted-animation.json --output-dir output/animated-scenes --report animation-status.json
python3 scripts/retrieve-animation-clips.py --tasks submitted-animation.json --output-dir output/animated-scenes --report animation-download-status.json --download
```

Downloads refuse to replace existing files and use temporary files before publication. The adapter checks that URLs use HTTPS/public addresses, rejects redirects, limits each clip to 256 MiB and performs a basic MP4 signature check. For stronger security, run against trusted task outputs only; task URLs are obtained from the Runway SDK. **This is not yet a synchronized final video.** Generated 5-second animations may require further timing adaptation for narration scenes. Test without API access using `python3 scripts/test-retrieve-animation-clips.py`.

## Phase 9.6 — Assemble animated clips with narration

After downloading completed clips from Phase 9.5, use the existing Phase 9 scene plan to create a single 720p MP4. Each scene clip is looped or trimmed to its narration-aligned duration. FFmpeg renders scenes **sequentially**, to limit peak memory usage, then concatenates video and combines it with the original narration. The final output refuses overwrites and is staged until successful completion.

```bash
mkdir -p output/video
python3 scripts/assemble-animated-video.py --plan scene-plan.json --clips-dir output/animated-scenes --output output/video/animated-story.mp4
python3 scripts/test-assemble-animated-video.py
```

This requires FFmpeg, available disk space, a valid source audio file and one `scene-0001.mp4` etc. per planned scene. The plan must start at zero, have no gaps/overlaps and cover the narration duration. Generated clips are not lip-synced; looping short clips may look repetitive. FFmpeg stream timing may differ slightly from nominal scene boundaries due to frame quantization; inspect the output with ffprobe and listen before publishing. This standalone assembly utility is not yet an automatic end-to-end single-command workflow.

## Phase 9.7 — Guided animation workflow

The optional `scripts/animation-workflow.py` CLI wraps individual production stages with consistent defaults. It **does not automatically submit paid requests or download media**, and does not yet offer one-command fully automated animation. It deliberately supports explicit, separately repeatable stages so failed phases can be rerun without repeating previous work.

```bash
python3 scripts/animation-workflow.py --stage transcribe --audio inputs/audio/narration.m4a --language hi
python3 scripts/animation-workflow.py --stage plan --style mythological_3d --scene-seconds 8
python3 scripts/animation-workflow.py --stage preview-images --limit 5
# Review scene plan and prompts. Explicitly use the Phase 9.3 paid API command if desired.
# Host approved images, then preview animation generation:
python3 scripts/animation-workflow.py --stage preview-animation --image-urls scene-image-urls.json --limit 5
# Submit Runway jobs with the explicit Phase 9.4 --execute command, then:
python3 scripts/animation-workflow.py --stage retrieve --tasks submitted-animation.json
# Download clips separately using the Phase 9.5 --download command; then:
python3 scripts/animation-workflow.py --stage assemble --clips-dir output/animated-scenes --output output/video/animated-story.mp4
```

Review the result of every stage. The orchestration does not provide transcript accuracy guarantees, image hosting, paid-service authorization, polling, retries, automatic downloading or character lip-sync. Run `python3 scripts/test-animation-workflow.py` for offline checks.

## Phase 9.8 — Monitor existing animation generation jobs

To poll **existing** Runway image-to-video tasks without submitting new jobs or downloading media, use `scripts/monitor-animation-jobs.py`. The command checks task IDs from a Phase 9.4 submitted manifest, with bounded polling (`--interval` seconds, `--max-checks`) and a new no-overwrite status JSON report. It never calls video generation endpoints. Successful terminal statuses return exit code 0; any failed or still-running tasks after the check limit return exit code 2; setup/API errors return exit code 1.

```bash
python3 scripts/monitor-animation-jobs.py --tasks submitted-animation.json --report animation-poll-01.json --interval 30 --max-checks 10
python3 scripts/test-monitor-animation-jobs.py
```

Requires `runwayml`, `RUNWAYML_API_SECRET` and network access. Polling may have API rate limits. To check again, supply a **new** report name. It does not cancel or retry generation, download clips, or recover failed tasks automatically. Scene-to-video assembly remains a separate stage.

## Phase 9.9 — Animation clip readiness before final assembly

After downloading Runway clips, validate the entire scene collection before starting an expensive final FFmpeg render. The checker requires `ffprobe`, a Phase 9 scene plan, and clips named `scene-0001.mp4`, `scene-0002.mp4` etc. It reports missing, empty, unprobeable, and valid MP4s. An exit code of **0** means all clips are available and contain a video stream; **2** means some scenes need recovery; **1** indicates invalid input or a tool error.

```bash
python3 scripts/check-animation-clips.py --plan output/animation-workflow/scene-plan.json --clips-dir output/animated-scenes --report output/animation-workflow/clip-readiness-01.json
python3 scripts/test-check-animation-clips.py
```

The checker does not delete or redownload files, regenerate paid tasks, or modify final videos. Supply a new report filename for another pass. Video stream presence and a positive reported duration do not guarantee visual quality or perfect narration synchronization.

## Phase 9.10 — Synthetic end-to-end animated video integration smoke

Run `python3 scripts/test-animation-e2e-smoke.py` to exercise the **real FFmpeg/ffprobe binaries** through the Phase 9.9 clip readiness checker and Phase 9.6 assembly pipeline. The test generates two 1-second synthetic animated-source clips and 4 seconds of narration audio in a temporary directory, loops each visual scene to its 2-second timeline slot, and checks the final MP4 includes audio/video with reasonable duration alignment. It also covers a missing-scene assembly failure, corrupt clips, and the refusal to overwrite a final output. The test requires ffmpeg/ffprobe and no model/API credits.

This smoke does **not** test real AI clips, transcription accuracy, provider communication, lip sync, or a 925-second narration on the user's laptop. Real media performance and end-to-end quality remain separate qualifications.

## Phase 9.11 — Prepare a small no-cost animation pilot

Before requesting dozens of paid AI clips, prepare a bounded preview plan from a completed Phase 9.1 scene plan:

```bash
python3 scripts/prepare-animation-pilot.py --plan output/animation-workflow/scene-plan.json --output output/animation-workflow/pilot-plan.json --seconds 30 --max-scenes 5
python3 scripts/test-prepare-animation-pilot.py
```

This prepares **up to 30 seconds and five scenes**, never invokes an AI provider, and does not change the source transcript or audio. It clips the final visual scene at the time limit. The resulting pilot scene plan still references the original full narration; **trim the narration into a separate audio file and update the pilot JSON's `audio` field before final assembly**. For example: `ffmpeg -i inputs/audio/narration.m4a -t 30 -c:a aac pilot-narration.m4a`, adjusting `-t` to the actual reported pilot duration. The full paid-generation workflow, image hosting and real-provider validation remain outside this safe planning stage.

## Phase 9.12–9.14 — Pilot audio, preview and integration recovery

This combined change restores the Phase 9.12 narration trim and Phase 9.13 preview workflow after their original PRs became conflicted, then adds an FFmpeg integration smoke. Prepare an initial pilot scene plan with Phase 9.11, trim its matching audio, and preview image/animation requests **without paid calls**:

```bash
mkdir -p output/animation-workflow
python3 scripts/prepare-animation-pilot.py --plan output/animation-workflow/scene-plan.json --output output/animation-workflow/pilot-plan.json --seconds 30 --max-scenes 5
python3 scripts/prepare-pilot-audio.py --plan output/animation-workflow/pilot-plan.json --audio-output output/animation-workflow/pilot-narration.m4a --plan-output output/animation-workflow/pilot-ready.json
python3 scripts/preview-animation-pilot.py --pilot output/animation-workflow/pilot-ready.json --workdir output/animation-workflow --limit 3
python3 scripts/test-pilot-integration.py
```

The prepared plan preserves scene timing while separately recording the measured AAC audio duration. The smoke uses real FFmpeg to ensure short narration trimming, timeline consistency and no-overwrite output safety. Paid AI generation, image hosting, downloading clips, and real media final assembly still require separate explicit steps.

## Phase 9.15 — Real-provider single-scene pilot preparation

Before attempting AI animation for the full narration, prepare a **single scene** and review the generation request. This tool does not call paid APIs, upload personal media, download results, or produce an animation.

```bash
python3 scripts/prepare-provider-pilot.py --pilot output/animation-workflow/pilot-ready.json --image-url https://example.com/your-approved-scene.png --plan-output output/animation-workflow/provider-scene-plan.json --urls-output output/animation-workflow/provider-image-urls.json
python3 scripts/animate-scene-images.py --plan output/animation-workflow/provider-scene-plan.json --image-urls output/animation-workflow/provider-image-urls.json --output output/animation-workflow/provider-preview.json --limit 1
```

To **actually submit a paid generation** after independently reviewing pricing and authorizing the request, you must separately run `scripts/animate-scene-images.py` with `--execute` and a configured `RUNWAYML_API_SECRET`. The provider adapter currently requests a five-second clip. Preparing a one-scene plan does not trim the narration to that scene's endpoint; the existing full pilot audio is still referenced and **must be separately trimmed** before assembling this one-scene output. The URL should point to an image you are authorized to share with the animation provider. No real Runway job, downloaded video or final media quality has yet been tested.

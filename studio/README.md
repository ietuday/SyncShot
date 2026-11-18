# SyncShot Studio

React starts jobs and downloads the generated MP4. Angular shows the current API session's render history. Node runs the existing Go renderer after Python checks the narration and image inputs.

## Run locally

Install Go 1.22 or later, Node.js 22.22.3+, 24.15+, or 26+ (supported release lines), Python 3, and FFmpeg (including ffprobe). From the repository root:

```sh
mkdir -p inputs/audio inputs/images output
go build -o output/syncshot-studio-renderer ./cmd/syncshot
cd studio
npm ci
```

Start `npm run api` and `npm run dev` in separate terminals from `studio`. Open http://127.0.0.1:5173/ for the studio and http://127.0.0.1:5173/angular/ for history. Select one narration and up to 200 images in the studio, then click **Render video**. Each upload can total up to 512 MB. Photos start in filename order and can be moved up or down. Choose a motion and transition, and optionally add an SRT file. **Preview 10 seconds** plays a short sample with those settings. Scene timing can vary from the full render. Use **Plan scenes** to see the full render’s start and end times and assigned photos before encoding. Choose a target scene length or let the planner use the photo count. With more scenes than photos, the planner cycles through the selected order. With an SRT file, the plan shows each caption once in the scene active at its start. At a crossfade, the incoming scene owns new captions. Planning uses narration duration and runs locally without an AI API.

A bodyless `POST /api/jobs` still uses the original `inputs/audio` and `inputs/images` folders. The render bar tracks FFmpeg output time across visual chunks and the final stitch. It reaches 100% once the MP4 is available. Browser uploads generate the full MP4. Folder-based API jobs also generate Shorts.

The API binds to loopback and accepts one render at a time in low-memory mode. Uploaded input files are removed when the job finishes. Job status is in memory and resets when the API restarts. Each run's MP4 stays under `output/studio/<job-id>/`. Set `SYNCSHOT_INPUTS`, `SYNCSHOT_RUNS`, or `SYNCSHOT_BIN` to override local paths.

Run `npm run build` to compile both frontends. The dev server proxies `/api` to the local Node service.

## Optional automatic captions

Install `faster-whisper` into the Python environment used by Studio, for example with `python3 -m pip install faster-whisper` inside a virtual environment. Activate that environment when starting the API, or set `SYNCSHOT_PYTHON` to its Python executable.

Set **Captions** to **Transcribe locally with Whisper**. Choose Hindi, English or automatic detection. Studio uses the multilingual tiny model with CPU int8 inference. The first automatic-caption job may download model weights. Subsequent jobs can use the cached model. Each plan, preview or render transcribes its uploaded narration before processing the captions.

## GitHub Pages browser demo

The `feature/studio-foundation` workflow builds Vite with `VITE_DEMO_MODE=true` and deploys the static frontend to `/SyncShot/studio/` while preserving the original homepage. In browser demo mode you can generate a sample 60-second scene plan, choose local photo names, adjust pacing and export CSV; it does not upload files, invoke Whisper, or produce MP4s. Real video rendering remains available only with the local Node/Go API. Enable **GitHub Actions** as the Pages build source in repository Settings → Pages if deployment is not active.

## Browser scene editor

In GitHub Pages demo mode, select sample photo names or upload images locally, plan scenes, then drag scene cards or use arrow buttons to reorder them. Per-scene duration fields recalculate all following scene timestamps and the CSV export. Uploaded thumbnails use temporary browser object URLs only and are revoked on change/unmount. These demo edits do **not** modify the Go renderer's live job settings, and the edited duration can differ from narration length.

## Scene preview (browser demo only)

After **Plan scenes**, the Visual scene editor has Play, Pause, Restart, and seek controls. It shows user-selected photos in order, or named sample placeholders, at the edited scene timings. This is an in-browser slideshow to review composition and pacing, not a produced video, and does not preview actual Go renderer crossfades or sound. It leaves the preserved original GitHub Pages homepage unchanged.

## Phase 4: Editable timeline rendering (local API)

When the Node/Go API is running locally, upload an audio file and photos, then **Plan scenes**. Reorder the scenes or edit the visible durations. Select **Render edited timeline** to upload the source media and a versioned JSON timeline, then generate a real MP4 from the edited order and durations. The API checks image references against the current uploaded filenames, validates duration/motion, and requires the edited visual runtime to match measured audio within 0.06 seconds. The Go manual-timeline renderer handles the full output at 720p. Existing automatic previews and renders stay available separately. Edited manual timelines currently support **full render only** (not the 10-second MP4 preview); browser timeline playback is a slideshow. For low-memory computers, manual timelines currently use the single-pass Go rendering path rather than the chunked automatic renderer. GitHub Pages remains a frontend-only demo and cannot run the Go/Node backend.

### Output, cancellation, and timeline export

The local Studio offers 720p and 1080p output presets. 1080p rendering uses more CPU and RAM. While a local render is active, **Cancel active job** sends a cancellation request to the Node API, which aborts the Go child process and marks the job cancelled. Cancelled jobs do not publish a completed MP4. The scene editor also has **Export timeline JSON** for saving the browser-authored, version 1 timeline. JSON uses uploaded photo **names** rather than filesystem paths; the Node API maps those names to files from the new upload and refuses unknown or duplicated names. A saved JSON file is a portable description, not an automatically restored Studio session.

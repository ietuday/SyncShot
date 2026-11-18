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

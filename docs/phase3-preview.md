# Phase 3.5 — Fast preview and cinematic rendering profiles

Preview mode is opt-in and does not overwrite `final.mp4`. Add to the CLI's `pipeline.Config`:

```go
PreviewSeconds: 15,
RenderProfile: "720p",
```

The pipeline trims a **temporary narration WAV** to up to the first 15 seconds, reuses existing input images, renders `output/video/preview.mp4`, and skips Shorts generation. The source audio and `output/video/final.mp4` are never modified by preview mode. Because image pre-processing still runs, this is faster for rendering but not a full lightweight pipeline.

Set `PreviewSeconds: 0` for full-length video generation. Set `RenderProfile: "1080p"` or leave it empty for 1920x1080. Setting `RenderProfile: "720p"` renders automatic cinematic scenes at 1280x720. Manually authored JSON timelines define their own resolution and currently cannot use the 720p profile or preview mode.

Preview mode requires `CinematicEnabled: true`. If background music is enabled, its fade duration must fit within the preview duration. Existing subtitle import/transcription applies to the current audio (in preview mode this is the trimmed WAV); use short test clips if you enable transcription to avoid unnecessary work.

For a typical first test:
```sh
go test ./internal/stages ./internal/pipeline
go run ./cmd/syncshot
ffplay output/video/preview.mp4
```

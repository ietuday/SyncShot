# Phase 5.4 — Production CLI (JSON configuration)

SyncShot now supports an optional JSON configuration file, command-line overrides, a preflight dry run and an overall render timeout. When no flags or config file are specified, existing defaults remain unchanged.

## Examples

    go run ./cmd/syncshot --dry-run
    go run ./cmd/syncshot --config ./syncshot.json --fps 30 --chunk-scenes 4
    go run ./cmd/syncshot --config ./syncshot.json --timeout 2h
    go run ./cmd/syncshot --audio-dir ./inputs/audio --images-dir ./inputs/images --output ./output/video/final.mp4

Example syncshot.json (Go field names are accepted by JSON decoder):

    {
      "FPS": 24,
      "CinematicEnabled": true,
      "CinematicChunkScenes": 4,
      "RenderProfile": "720p",
      "ClipSeconds": 50,
      "MaxWorkers": 4
    }

JSON fields override defaults; CLI flags override JSON. Unknown JSON keys are rejected. The startup check looks for ffmpeg and ffprobe in PATH and validates input directories and config constraints. Dry-run checks configuration and input directory entries but does not decode media, render scenes or write output. It is a preflight, **not** an exact video scene planner or media-integrity guarantee.

The --timeout flag bounds the whole pipeline and propagates context cancellation to context-aware rendering calls. Existing utility methods that use independent contexts may still require follow-up hardening. YAML parsing, per-stage timeouts, advanced dry-run media profiling and configurable FFmpeg paths are not part of this initial change.

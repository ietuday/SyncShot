# SyncShot-Go

Put audio in inputs/audio and images in inputs/images
Run: go run ./cmd/syncshot

## Memory-conscious rendering (Phase 8.0)

The normal workflow is unchanged: put narration in `inputs/audio/`, put photos in `inputs/images/`, then run `go run ./cmd/syncshot`. Automatic cinematic scenes now render in **two-scene chunks by default**, with **two parallel image-processing workers** (previously the default rendered the full timeline in one FFmpeg graph and used four image workers). This aims to reduce peak memory on laptops such as 12 GiB Ubuntu machines.

For lower memory pressure, run `go run ./cmd/syncshot --chunk-scenes 1`. To explicitly restore the old unchunked cinematic path, use `--chunk-scenes 0`. Both `CinematicChunkScenes` and `MaxWorkers` remain configurable via JSON.

**Validation:** run `go test ./...` and retry your actual 15-minute narration with 10 images. The change does not yet prove that all long media jobs fit in 12 GiB RAM; monitor `free -h` and kernel OOM messages. Explicit cinematic timelines still use their separate renderer, and are not affected by this default.

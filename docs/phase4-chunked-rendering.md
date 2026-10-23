# Phase 4.2 — Opt-in chunked cinematic rendering

For long automatic cinematic timelines, rendering all scenes in one FFmpeg filtergraph can consume substantial resources. Chunk mode limits each FFmpeg video filtergraph to a specified number of scenes, renders each group sequentially, and concatenates the finished MP4 segments.

Enable it in `pipeline.Config`:

```go
CinematicEnabled: true,
CinematicCrossfade: 0,
CinematicChunkScenes: 4, // 0 disables chunk mode
```

This initial mode requires an automatically generated timeline, **zero crossfade**, and **no background music, subtitles, or subscribe/bell overlays**. Other settings are rejected by validation rather than silently dropping features. It preserves the previous renderer when disabled.

Segment narration audio is trimmed from the original input at cumulative scene boundaries. All generated segments are held in a temporary directory; the combined MP4 is validated for duration and only then published. Cancellation or failures do not publish incomplete output. The temporary files are deleted afterward.

Use `go test ./internal/cinematic` and verify a representative long clip before merging. Stream-copy MP4 concatenation can introduce small audio timing differences around chunk joins due to codec priming; seamless cross-chunk transitions, subtitles, and background music will be implemented separately.

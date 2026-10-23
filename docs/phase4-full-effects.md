# Phase 4.3 — Chunked cinematic rendering with full effects

Opt into bounded **scene-group** rendering with `CinematicChunkScenes`. The new path keeps internal scene crossfades in each chunk and joins neighboring chunk outputs with an FFmpeg crossfade. Original narration, optional background music with sidechain ducking, optional SRT subtitles, and subscribe/bell overlays are applied on the combined full timeline.

Example (inside `pipeline.Config`):

```go
CinematicEnabled: true,
CinematicAutoSceneSeconds: 30,
CinematicCrossfade: 0.5,
CinematicChunkScenes: 4,
MusicPath: "./inputs/music/background.mp3",
MusicVolume: 0.15,
MusicFadeSeconds: 1.5,
MusicDucking: true,
SubtitleMode: "import",
SubtitleSRTPath: "./inputs/subtitles/captions.srt",
```

`CinematicChunkScenes: 0` retains the existing single-render path. This phase continues to support automatic cinematic timelines; manual JSON timelines remain outside the chunking route.

The new pipeline performs one sequential FFmpeg render per bounded group, plus a global composition pass containing **one video input per group**. Audio is taken from the original narration and mixed continuously in the global pass, so narration/music is not stream-copy concatenated at chunk seams. Subtitles are muxed once on the full timeline as selectable `mov_text`, rather than burned in.

**Trade-off:** The final join still has an FFmpeg filtergraph proportional to the number of chunks; it is not constant-memory for arbitrarily long videos. Each visual chunk is encoded once and the final output is encoded again; measure CPU, memory, output time and audio continuity before release. Preview and default single render behavior remain opt-in/unchanged.

Test: `go test ./internal/cinematic -run 'TestPartitionEffectsPreservesDuration|TestRenderChunkedEffectsWithFullTracks' -v`.

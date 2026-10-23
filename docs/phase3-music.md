# Phase 3.3 — Background music and audio ducking

Music is **opt-in**. The cinematic renderer keeps the narration audio unchanged when music is disabled.

Set in `cmd/syncshot/main.go` inside `pipeline.Config`:

```go
MusicPath: "./inputs/music/background.mp3",
MusicVolume: 0.15,
MusicFadeSeconds: 1.5,
MusicDucking: true,
```

Music is looped to fill the narration timeline (FFmpeg `-stream_loop -1`). FFmpeg mixes the tracks into **one audio stream**. `MusicVolume` scales the background track linearly (0–1). `MusicFadeSeconds` applies music fade-in and fade-out. When `MusicDucking` is true, FFmpeg's `sidechaincompress` automatically reduces the music when narration signal is present (threshold 0.03, ratio 8, attack 20ms, release 300ms). The narration itself is not compressed.

Disable by leaving `MusicPath: ""` and the other music fields at their zero values. This feature currently requires `CinematicEnabled: true`.

Use music you have permission to include in your videos. Choose `MusicVolume` around 0.10–0.20 for narration-oriented videos, then listen and adjust. The ducking is signal-driven rather than semantic speech detection. It will also respond to loud background sounds present in narration.

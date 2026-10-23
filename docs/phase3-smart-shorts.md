# Phase 3.4 — Smart YouTube Shorts

Smart Shorts use the existing vertical FFmpeg rendering and transactional output publishing.

Add these optional settings to the CLI `pipeline.Config`:

```go
SmartShortsEnabled: true,
SmartShortsCrop: "center", // "left", "right", or "pan"
ClipSeconds: 50,
```

When `SmartShortsEnabled` is true and automatic cinematic scene planning is used, Shorts prefer cuts at multiples of `CinematicAutoSceneSeconds` (default 30 seconds) when a boundary is at least 60% of the requested Short length. This is **timing-based scene alignment**, not a spoken-topic or semantic highlight detector. Each Short remains no longer than `ClipSeconds`; a shorter final Short is possible. If a manually authored timeline is used, fixed-duration cuts are retained for now.

The crop modes choose landscape-to-portrait framing: `center` (default), `left`, `right`, or `pan` (the existing animated zoompan mode). These are geometric crop presets; they do not detect faces or subjects. Subtitles embedded in the source MP4 are preserved as optional selectable subtitle tracks in the resulting Shorts. Burned-in captions are not yet supported.

With `SmartShortsEnabled: false` and `SmartShortsCrop: ""`, the legacy fixed-cut, center-crop behavior remains the default. The feature requires no external AI service.

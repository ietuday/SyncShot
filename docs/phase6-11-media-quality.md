# Phase 6.11 — Encoded media quality gate

The two-second real FFmpeg benchmark smoke test now probes the rendered MP4 and verifies it contains one H.264 video stream at 1280×720, at least one AAC audio stream, an expected 1–5-second duration, and no substantial (>1.5-second) mismatch between stream and container durations where stream durations are reported.

The resulting `media-quality.json` is included in the CI benchmark-evidence artifact. This is a mechanical codec, resolution and duration check; it does not verify subjective visuals, speech alignment, subtitle quality or playback across devices. Real 15–60-minute tests remain necessary for production qualification.

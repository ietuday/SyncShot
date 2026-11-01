# Phase 7.4 — Subtitle timing boundaries

The subtitle/music CI fixture now compares authored SRT timestamps to the actual rendered MP4 duration (from ffprobe). It rejects invalid, overlapping and out-of-duration cues and archives `subtitle-cues.json` with cue starts, ends and midpoints. Unit tests cover valid and invalid ranges.

This does **not** verify captions actually appear at those timestamps in pixels: this check validates the imported subtitle specification against media duration, not burn-in correctness. Audio ducking remains enabled in the integration fixture but attenuation depth has not been quantified. Frame-level or perceptual testing and actual human narration remain outstanding.

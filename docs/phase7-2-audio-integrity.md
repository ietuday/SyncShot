# Phase 7.2 — Audio integrity qualification

The varied-media rendering workflow now decodes the produced MP4's first audio stream with FFmpeg `volumedetect`. A passing result requires measurable finite average and peak volume (defaults: mean >= -65 dB and peak >= -45 dB). The workflow records `audio-integrity.json` alongside existing video-quality and benchmark evidence.

This detects absent, undecodable and silent/very quiet audio for this known synthetic fixture. It **does not** certify speech intelligibility, clipping, synchronization, voice quality, background music ducking, nor legitimate quiet content. Volume thresholds are test-specific and configurable via CLI options. Real voice, subtitle and music integration still needs separately designed tests.

Local check: `python3 scripts/check-audio-integrity.py path/to/video.mp4`.

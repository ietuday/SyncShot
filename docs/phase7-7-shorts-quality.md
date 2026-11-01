# Phase 7.7 — Shorts media qualification

A GitHub Actions workflow renders varied synthetic media with Shorts enabled and verifies every generated MP4 has 1080×1920 H.264 video, AAC audio, a positive duration no longer than eight seconds (plus 0.5-second encoding tolerance), and audio that FFmpeg can fully decode. The workflow exports `shorts-quality.json` alongside the long-video quality metrics.

This checks structural correctness and absence of audio decoding errors. It does not inspect perceptual visual framing, subtitle safety zones, music ducking in the Shorts, or subjective quality. All sources are synthetic.

# Phase 7.3 — Subtitle and music integration fixture

A dedicated CI workflow generates three varied still images, 18 seconds of synthetic narration, a low-volume 220 Hz background track and an imported two-cue SRT. It runs SyncShot with cinematic chunked rendering, subtitle import, MusicVolume 0.15 and MusicDucking enabled. It checks MP4 structure, duration, decodable non-silent audio and outputs benchmark evidence.

**What this proves:** that this fixture can render successfully through the combined subtitle-and-music pipeline. **What it does not prove:** precise caption timing, on-screen text recognition, music ducking depth, subjective audio quality, speech clarity or real-world media compatibility. Those need separate signal/visual validation tests.

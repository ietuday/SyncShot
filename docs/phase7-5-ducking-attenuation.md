# Phase 7.5 — Frequency-selective music ducking verification

The CI integration fixture now renders identical 18-second generated media twice: first with MusicDucking enabled, then with it disabled as a matched reference. A Python analyzer decodes both audio tracks and measures the 220 Hz synthetic music component between 5 and 10 seconds using quadrature tone correlation. The check requires at least 2 dB reduction in the ducked version and archives `ducking-attenuation.json`.

This is a reproducible narrow-band test, not a general loudness or perceptual evaluation. It assumes the generated narration is 330 Hz and music is 220 Hz; real speech and music overlap spectrally, so subjective listening and further tests remain necessary. The two renders cost additional CI time. It does not establish that ducking recovers correctly between speech segments because this particular narration tone is continuous.

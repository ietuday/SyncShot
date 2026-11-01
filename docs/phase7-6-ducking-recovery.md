# Phase 7.6 — Music recovery during narration gaps

The subtitle/music integration fixture now mutes its 330 Hz narration tone from 6–11 seconds while keeping the 220 Hz music tone continuous. A matched music-ducking-off reference is rendered alongside the ducking-on video. The CI analyzer measures music attenuation during active narration (2–5 seconds) and silence (8–10 seconds), requiring at least 2 dB attenuation during narration and at least 2 dB relative recovery during the gap. `ducking-recovery.json` is included in the evidence artifact.

This verifies one synthetic audio recovery case. It does not measure subjective smoothness, clipping, natural speech or complex music, or guarantee music reaches its exact unmodified level.

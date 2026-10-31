# Phase 6.14 — 15-minute synthetic qualification

The new **Fifteen minute qualification** workflow attempts a 900-second synthetic narration with a 720p chunked video, FFprobe-based encoded media verification, input fingerprints and downloadable benchmark evidence. It runs when this workflow changes in a PR and can also be manually dispatched after merge.

This workload may take substantial CI resources and time. The workflow has a 60-minute job limit and the render has a 50-minute deadline. Failure under those constraints must be investigated; no performance success is assumed before CI finishes.

The content is synthetic (sine-wave narration and two color images) and is not representative of real narration, images, subtitles, overlays or music. Passing does not imply production performance qualification at 30/60 minutes or playback quality.

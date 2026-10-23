# Phase 3.1 — Automatic scene planning

Set `CinematicAutoSceneSeconds` (default `30` in `cmd/syncshot/main.go`) to split a long narration into roughly equal scenes. Images cycle in sorted filename order; with one image, the same artwork is reused across the scene boundaries. A 22-minute narration with a 30-second target produces about 45 scenes. Scenes use the selected cinematic motion and configured crossfade.

The planner distributes integer video frames, adds outgoing crossfade overlap and keeps the total composited duration within one video frame of the narration.

Set `CinematicAutoSceneSeconds: 0` to retain Phase 2's original one-scene-per-image behavior.

**Limitations:** This is timing-based planning, not speech-to-text or semantic image matching. For story-specific scenes, use the existing `CinematicTimelinePath` JSON timeline. FFmpeg has to handle one stream for every planned scene; for very long narration or limited RAM use a larger scene target such as 60 or 90 seconds. The existing precise narration probe and publishing protections are retained.

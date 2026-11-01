# Phase 6.16 — 60-minute synthetic video qualification

The `Sixty minute qualification` GitHub Actions workflow attempts a **3,600-second** synthetic narration and a 720p video render. It checks encoded output with FFprobe, writes benchmark summaries, and publishes evidence as a 14-day artifact. The workflow runs automatically when its YAML changes in a pull request and also supports manual dispatch.

The workflow uses a 120-minute job limit and a 100-minute rendering deadline. The successful results of the previous 15- and 30-minute workflows do **not** establish that this hour-long run will succeed; verify the completed CI result before merging.

This synthetic test uses generated tones and two color images. Real production input combinations, subtitle synchronization, music ducking, complex image transitions, user-visible playback quality, and comparative memory performance remain separate qualification steps.

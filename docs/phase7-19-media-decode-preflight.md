# Phase 7.19 — Production media decodability preflight

The production-media qualification entrypoint now probes selected audio and image files with FFprobe, then decodes every recognized input with FFmpeg (`-xerror`) before starting the render. Missing streams, broken decodes, and per-file timeouts fail preflight. The default timeout is 120 seconds per file, configurable through `SYNC_SHOT_DECODE_TIMEOUT_PER_FILE`.

The preflight runs on the machine with actual media. GitHub CI exercises mocked success/failure decoder paths, not private user sources. This checks whether input streams decode; it does not verify caption accuracy, crop relevance, perceived image fidelity, or source content correctness. Large source collections can make the full decode preflight expensive. Preflight failures occur before the per-run status report is created.

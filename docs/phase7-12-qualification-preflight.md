# Phase 7.12 — Production media preflight

The real-media qualification command now checks the supplied fingerprint input paths and performs a SyncShot CLI `--dry-run` before starting the measured render. This catches missing selected inputs and invalid rendering configuration early, ahead of expensive media processing.

The preflight uses the same `--config` and `--output` overrides as the render. The existing protection against overwriting output remains in place.

**Limitations:** CLI dry-run checks configuration and dependencies, but does not guarantee all media is decodable or that a long render will succeed. Operators still need complete source selections in `SYNC_SHOT_BENCHMARK_INPUTS` and manual playback review. This phase does not execute private production media in CI.

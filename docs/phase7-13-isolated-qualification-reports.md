# Phase 7.13 — Isolated real-media qualification reports

Each call to `scripts/qualify-production-media.sh` now creates a unique `qualification-XXXXXXXX` directory below the requested report directory. The benchmark runner, `qualification-summary.json`, `media-quality.json`, and `audio-integrity.json` all use that run-specific directory. This prevents older `run-*` folders from polluting the new result, or old summaries being mistaken for the latest render.

The command prints the exact evidence directory. Failed runs retain their directory for diagnostic inspection; success still requires a fresh video and quality checks. Do not assume a report directory indicates success without verifying the script exit code.

This improvement does not replace an actual production-media render, and the existing CI validates script syntax but does not execute private user media.

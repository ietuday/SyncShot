# Phase 7.20 — Actual FFmpeg decoder fixture tests

The Go Phase 1 workflow now generates a small WAV narration file and PNG still using FFmpeg, verifies both using the actual `check-qualification-media-decode.py` preflight, deliberately corrupts the PNG contents, and asserts the second validation fails. This adds real decoder coverage on top of earlier mocked Python unit tests.

This deliberately small fixture does not represent real user footage, media diversity, or long production workloads. Private real media qualification remains to be run separately.

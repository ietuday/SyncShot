# Phase 7.14 — Production qualification failure reporting

Once a unique qualification evidence directory has been created, the qualification script tracks stages `benchmark`, `benchmark_summary`, `video_quality`, `audio_integrity`, and `complete`. Its Bash EXIT trap records `status.json` with the final stage, exit code, success/failure state, and UTC timestamp. When a command fails, the script prints the evidence directory for investigation; benchmark logs and any earlier reports remain available there.

Preflight failures occur **before** a run evidence directory is allocated and therefore do not produce `status.json`. The script's exit status remains authoritative. The status report records a failure location, not the complete exception text; inspect retained logs and stderr for details. GitHub CI checks shell syntax; real private media must be tested by its owner.

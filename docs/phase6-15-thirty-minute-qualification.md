# Phase 6.15 — 30-minute synthetic qualification

A new GitHub Actions workflow executes a 1,800-second synthetic narration and 720p chunked render on workflow-related pull requests or manual dispatch. It runs the existing FFprobe output-quality gate and uploads evidence as a 14-day artifact. The qualification script now accepts 10–1800 seconds.

This synthetic workload only uses two solid-color images and generated tones. A successful CI run proves this test path can render a 30-minute output on the chosen runner, **not** general production performance, subtitles/BGM correctness, or representative real-world workload quality.

CI must finish green before merge; failure due to runner timeout or resources is still a failure needing investigation.

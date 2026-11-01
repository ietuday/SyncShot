# Phase 7.23 — Paired qualification comparison

A dedicated GitHub Actions workflow generates six seconds of synthetic narration and two images, then runs the *entire* production qualification command twice against exactly the same generated sources and config on the same CI runner. It compares the resulting benchmark reports using the existing input-fingerprint and workload-ID consistency checks, reporting realtime factor, process RSS and FFmpeg RSS. Evidence includes both summaries and the comparison JSON.

The CI gate deliberately permits a **200% regression**, because extremely short executions on shared runners are noisy. This is intended to exercise the comparison pipeline and expose gross regressions, not to establish a stable performance budget. Follow-up production performance benchmarking needs repeated longer-duration runs on controlled hardware with a vetted baseline and real permitted media.

# Phase 7.23 — Paired qualification comparison

A dedicated GitHub Actions workflow generates six seconds of synthetic narration and two images, then runs the *entire* production qualification command twice against exactly the same generated sources and config on the same CI runner. It compares the resulting benchmark reports using the existing input-fingerprint and workload-ID consistency checks, reporting realtime factor, process RSS and FFmpeg RSS. Evidence includes both summaries and the comparison JSON.

The CI gate deliberately permits a **200% regression**, because extremely short executions on shared runners are noisy. This is intended to exercise the comparison pipeline and expose gross regressions, not to establish a stable performance budget. Follow-up production performance benchmarking needs repeated longer-duration runs on controlled hardware with a vetted baseline and real permitted media.

## Phase 7.24 — Comparator contract hardening

The paired qualification E2E script now runs deterministic comparator contract tests before generating media. These validate identical runs, regression detection above 15%, acceptance at the exact threshold, rejection of mismatched workload IDs and input SHA-256 fingerprints, and rejection of zero, negative, NaN, and infinite metric values. Since the test is called by the existing workflow, these checks run on every relevant pull request without adding rendering time. The paired benchmark still has a wide 200% tolerance and is not a production performance certification.

## Phase 7.25 — Repeated-run median comparisons

The benchmark comparator accepts repeatable `--baseline-extra` and `--candidate-extra` report arguments. Every supplied report must contain exactly one valid benchmark run, with matching labeled workload IDs and matching SHA-256 input fingerprints. It uses the median of each of the three tracked metrics within each group, making comparisons less sensitive to isolated outliers. Without extra reports, existing single-run comparisons are unchanged.

Example: `python3 scripts/compare-benchmarks.py base1.json candidate1.json --baseline-extra base2.json --baseline-extra base3.json --candidate-extra candidate2.json --candidate-extra candidate3.json --max-regression-percent 15`.

Use the **same number of independent runs per group** as a benchmarking convention, and execute on comparable hardware under controlled load. The CI paired workflow continues to run just one baseline and one candidate, so this feature does not yet provide a repeated-run production performance certification.

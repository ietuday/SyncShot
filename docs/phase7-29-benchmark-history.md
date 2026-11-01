# Phase 7.29 — Archived benchmark history

This phase provides an **offline evidence aggregation** utility, not an automated measurement database. Download and unpack complete qualification evidence artifacts into separate directories and run:

```sh
python3 scripts/summarize-benchmark-history.py \
  ./evidence/run-001 ./evidence/run-002 \
  --output-dir ./evidence/history
```

Each input directory must include `run-manifest.json` and `paired-performance-comparison.json`. The utility checks the expected three metric names and numeric values, then exports `history.json` for processing and `history.md` for readable review. Input order determines report row order; files do not include trustworthy benchmark timestamps. Incomplete/older artifacts are rejected rather than silently dropped.

These entries represent comparisons performed in individual runs. They are **not a valid continuous trend** unless workloads, comparison setup, hardware and source revisions are comparable. The CI smoke-test threshold is still 200%; don't interpret these records as production certification. Future phases may fetch artifacts automatically and add timestamped, compatible reference baselines.

## Phase 7.30 — Selective artifact collection

The manual **Aggregate benchmark history** GitHub Actions workflow accepts 1–20 comma-separated GitHub Actions run IDs from completed *Paired production qualification comparison* runs. It downloads each run's `paired-qualification-evidence` artifact with `gh run download`, requires the manifest and comparison JSON, and passes the unpacked directories to the Phase 7.29 history summarizer. It uploads `history.json` and `history.md` together and publishes Markdown in the job summary.

To use it: Actions → Aggregate benchmark history → Run workflow → enter run IDs, e.g. `123456789,123456790`. Older runs whose artifacts have expired (14-day retention) fail explicitly. This workflow does not store a permanent trend database, discover historical runs automatically, or infer chronological measurement timestamps. Only compare entries with compatible workloads and testing environments.

## Phase 7.31 — Automatic recent-run discovery

On manual **Aggregate benchmark history** dispatch, leave `run_ids` blank to discover the latest successful `paired-qualification-comparison.yml` workflow runs. Choose `latest_count` (1, 3, 5, 10, or 20). The collector examines up to the latest 100 successful workflow runs and selects those with a non-expired `paired-qualification-evidence` artifact. Explicit comma-separated `run_ids` still take precedence.

This is a bounded lookback, not a permanent archive or scheduled collection job. Missing/expired artifacts remain unavailable. No automatic cron trigger is introduced; discovery is performed only when manually dispatched. Historic comparisons are only meaningful for compatible workloads and CI environments.

## Phase 7.32 — Visual trend exports

The history summarizer additionally emits `trend.csv` and a dependency-free `trend.svg`, plotting the three metric percentage changes across the **supplied evidence order**. Both are included automatically in the aggregated history artifact. The horizontal axis is a sequence number, **not** a measurement timestamp. This view is useful for spotting patterns only when the workload, runner characteristics, and baseline strategy are comparable across records. The chart is not a production performance certification and does not infer chronological ordering.

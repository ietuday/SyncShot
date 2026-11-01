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

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

## Phase 7.33 — Configurable regression alerts

The historical summary CLI now accepts `--alert-threshold-percent` (default 200). It produces `regression-alerts.json`, listing any metric whose candidate-over-baseline percentage exceeds this limit, with workload and revision identifiers. A detected regression exits nonzero **after** saving evidence, so GitHub Actions fails visibly while retaining diagnostic artifacts. Manual aggregate workflow dispatch exposes `alert_threshold_percent`. For example, use 15 only with repeated, controlled and comparable benchmark runs.

This is an **in-workflow alert**, not email, messaging, or issue creation. Different workloads or uncontrolled runners cannot be treated as reliable performance regressions; the default 200% CI allowance remains intentionally permissive.

## Phase 7.34 — Actionable CI regression summary

The history collector now also writes `regression-alerts.md` alongside structured `regression-alerts.json`. The Markdown lists the affected evidence directory, workload, metric, percentage change and abbreviated baseline/candidate commits. Manual collection displays this summary in the GitHub Actions job summary, including when threshold violations fail the job. No email, issue, or external notification is sent. Results remain subject to the comparability limitations described above.

## Phase 7.35 — Baseline workload compatibility gates

The history summarizer supports `--require-workload-id ID` and `--min-repetitions N` to reject evidence that lacks the desired workload or enough repeated qualifications. Both checks happen before writing reports or issuing regression alerts. The manual aggregation workflow exposes matching inputs. Use these gates to avoid mixing unrelated workloads or treating one-off results as robust measurements. Defaults preserve existing compatibility (no required workload ID and minimum of one run per side). These gates do not verify hardware, environment, media provenance, or statistical significance; they are only preliminary safeguards.

## Phase 7.36 — Environment provenance checks

Paired qualification evidence now records OS, CPU architecture, Python version, GitHub runner image and architecture, and the SHA-256 of the benchmark configuration. The history utility accepts `--require-matching-environment` (also available as a manual workflow toggle). When enabled, it rejects missing metadata and requires the recorded values to match across all selected artifacts before producing regression alerts. Previous artifacts lacking provenance are deliberately excluded in strict mode.

This is **metadata equality**, not proof of identical hardware performance: CPU model, load, kernel patch level, FFmpeg version, and media provenance remain uncontrolled. The config hash is sensitive to path changes as well as actual rendering settings. Keep default mode backward compatible with older artifacts, and use strict mode only for evidence collected under the new schema.

## Phase 7.37 — Toolchain and CPU provenance

Qualification evidence now records the first line of `ffmpeg -version`, the output of `go version`, and the CPU model string when available. Strict environment comparison requires these fields in addition to Phase 7.36's OS, architecture, Python, runner image, and config hash. Older artifacts without these fields are rejected in strict mode, while non-strict aggregation remains backwards compatible.

This check compares recorded identities, not measured hardware isolation or workload equivalence. The FFmpeg banner does not describe every linked codec library; CPU model equality does not capture load, frequency scaling, virtualization, or competing jobs.

## Phase 7.38 — Input drift verification

Use `--require-matching-inputs` (or enable the equivalent checkbox on manual history aggregation) to verify each referenced qualification report's SHA-256 input fingerprint and labeled workload ID. The gate checks every baseline and candidate report in each selected evidence artifact, then rejects mismatched fingerprints or workloads across artifacts *before* generating performance-regression alerts. Missing or malformed SHA-256 fingerprints, report references, and workload IDs fail validation. This option intentionally remains opt-in to allow historical datasets without complete report artifacts to be summarized in compatibility mode.

Fingerprints protect against comparing different benchmark inputs, but do not guarantee that files were collected from trusted machines or that all non-input environment factors are identical. Combine this check with `--require-matching-environment` and workload/repetition constraints for stronger evidence hygiene.

## Phase 7.39 — Archived report checksum verification

New paired qualification artifacts include `evidence-sha256.json` mapping each archived baseline/candidate qualification report filename to its SHA-256 checksum. The historical aggregator supports `--verify-evidence-sha256` (manual workflow checkbox). Strict verification rejects missing checksum manifests, missing or extra report references, and modified report bytes before producing history or alerts. Older artifacts without checksums can still be aggregated with strict verification disabled.

These hashes detect accidental corruption after the checksums were created. They are not cryptographic attestations of provenance: an attacker able to replace both reports and checksums can forge matching values.

## Phase 7.40 — Versioned audit metadata

New paired qualification manifests record `schema_version: 2`, a UTC generation timestamp, GitHub Actions run ID and attempt, repository, and workflow name. The history utility preserves those fields in `history.json`. Enable `--require-audit-metadata` (or the manual aggregation workflow checkbox) to require a version-2 manifest with a valid UTC timestamp and populated GitHub run identifiers. The check is opt-in for historical evidence collected before Phase 7.40. These self-reported fields support investigation and traceability but **do not authenticate evidence** or prove that it was generated by GitHub Actions; signed attestations are a separate future capability.

## Phase 7.41 — GitHub artifact attestations (manual workflow)

For a **successful manual** `Paired production qualification comparison` dispatch, a separate `attest` job downloads the completed benchmark evidence artifact, builds `paired-qualification-evidence.tar.gz`, and uses `actions/attest-build-provenance@v2` with GitHub OIDC to record a provenance attestation for the **archive bytes**. The workflow uploads the resulting archive as `attested-paired-qualification-evidence`. Pull-request runs deliberately do **not** receive OIDC or attestation write permissions.

After downloading the archive, use `gh attestation verify paired-qualification-evidence.tar.gz --repo ietuday/SyncShot` with a suitably recent GitHub CLI to verify the archive digest and signer provenance against GitHub's transparency-backed attestation record. Confirm the returned repository and workflow identity; do not rely only on an exit code if your policy requires a specific source ref or workflow. The attestation is associated with the workflow job that packaged the benchmark artifact, **not** a claim that every result was measured on isolated, trusted hardware. Offline history aggregation does not yet automatically perform attestation verification. Repository/GitHub plan settings and Actions attestation availability may affect manual dispatch results; this path requires a live manual run before it can be considered operationally validated.

## Phase 7.42 — Verified provenance gate during history aggregation

Manual **Aggregate benchmark history** dispatch now offers `require_attestation`. When enabled, the workflow discovers only successful runs with the `attested-paired-qualification-evidence` archive, downloads that archive, verifies its GitHub provenance with `gh attestation verify` (including the expected signer workflow), checks allowed archive entry paths, and only then extracts the reports for historical comparison. An invalid/missing attestation fails the job without falling back to unattested evidence. Explicit run IDs follow the same verification path.

This is opt-in to preserve compatibility with older benchmark artifacts. Attestation verification establishes GitHub workflow provenance for archive bytes, **not** trustworthy performance measurements or equivalent benchmark hardware. The manual archive-signing and verification paths still require a live `workflow_dispatch` test in this repository; ordinary pull-request CI cannot validate GitHub attestation availability or permissions.

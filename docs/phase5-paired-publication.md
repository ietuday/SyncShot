# Phase 5.2 — Paired video + Shorts publication

For normal full renders with Shorts enabled, the pipeline now renders the video into a same-directory stage file and generates the entire Shorts batch into a same-parent staging directory. Neither published destination changes until both artifacts have been fully rendered and validated. It then publishes the pair using a journaled replacement process.

## Recovery

- Before replacement, a journal is created at `<final-video>.syncshot-transaction.json`.
- Existing final video and Shorts are moved to `.syncshot-transaction-backup` paths, then new staged outputs are renamed to their destinations.
- On publication error, rollback restores both previous outputs from their backups.
- When a new run starts, an unfinished journal is detected and recovery runs first. Journal and backup files are normally cleaned after a successful commit.
- A missing required backup and missing prior destination stops recovery rather than inventing an output.

## Limitations

Two independent filesystem paths cannot be replaced with one atomic rename. Readers accessing video and Shorts **during** the short commit interval can observe different generations; the journal protects against interrupted publications and enables rollback/recovery, not simultaneous reader visibility. Full transactional visibility would require a versioned output directory with one atomically updated pointer. Keep final video and Shorts destinations on filesystems supporting atomic same-directory renames.

Preview runs and full renders with Shorts disabled continue to use the prior publication behavior. Run lock prevents simultaneous jobs using the same work directory, but distinct work directories targeting identical output locations must still be coordinated externally.

## Validation

```bash
go test ./internal/stages -run 'TestPublishVideoAndShorts|TestInvalidStagedShortPreservesPair|TestRecoverInterruptedPairPublication|TestRenameFailureRollsBackBothOutputs' -v
go test ./...
```

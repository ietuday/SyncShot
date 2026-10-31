# Phase 5.8 — Benchmark safety

The long-video benchmark now uses a unique run directory created atomically by mktemp, rather than a timestamp directory that could collide with another invocation.

The runner installs an EXIT/INT/TERM trap that attempts to terminate its running SyncShot process and immediate children if the benchmark is interrupted. Normal cancellation through SyncShot is still preferred; detached grandchildren may need manual inspection.

The summary reports output_bytes only when the command succeeds. Previously, a failed invocation could incorrectly report the size of a pre-existing final.mp4, which misrepresented a failure as having produced an artifact.

The standard Go Phase 1 CI now checks benchmark shell syntax with bash -n.

## Validation and limitations

    bash -n scripts/benchmark-long-video.sh
    bash scripts/benchmark-long-video.sh

Memory RSS values remain sampled estimates; the script does not replace controlled full-length media tests. The report still assumes the default output path, and for custom output paths the size column should not be interpreted as the produced file size.

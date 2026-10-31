# Phase 5.5 — Release engineering

## CI
Go Phase 1 and Phase 2 cinematic workflows now run on pushes to `syncshot-go`, in addition to pull requests (subject to the existing path filters). The release workflow builds tagged (v*) artifacts and can also be started manually from GitHub Actions.

## Releases
Before tagging, run the complete FFmpeg-enabled integration suite on Linux:

    go test -count=1 ./...
    go vet ./...
    bash scripts/smoke-test.sh
    bash scripts/cancel-smoke-test.sh

Then create a versioned tag from a reviewed `syncshot-go` commit:

    git switch syncshot-go
    git pull --ff-only
    git tag v0.1.0
    git push origin v0.1.0

GitHub Actions builds compressed artifacts with SHA-256 files for Linux (amd64/arm64), macOS (amd64/arm64) and Windows (amd64). Artifacts are attached to the workflow run, **not** published as a GitHub Release automatically. No tags are created by this PR.

## Runtime prerequisites
Release binaries **do not bundle FFmpeg or FFprobe**. Both executables must be installed and discoverable through PATH; verify them with `ffmpeg -version` and `ffprobe -version`.

Run from the directory containing your `inputs/audio` and `inputs/images` folders, or specify paths with CLI flags and a JSON config. Use `--dry-run` before your first full render. For production work, keep free disk space for intermediate chunks, final video, and Shorts staging.

## Known limitations
- The project does not yet publish signed binaries, SBOMs, or GitHub Releases automatically.
- Automated integration tests are Linux-based; macOS and Windows release files are cross-compiled, not integration-tested on native hosts.
- This workflow builds snapshot archives through workflow_dispatch but leaves release publication manual.
- Post-merge CI still uses existing path filters; documentation-only commits do not trigger all test suites.
- Long-duration memory and rendering benchmarks, plus real-video playback review, remain necessary for production qualification.

# Enhanced SyncShot-Go integration

This branch is intended to merge the enhanced SyncShot-Go implementation into `syncshot-go`.

## Planned changes

- Validate and filter input audio/images.
- Propagate FFmpeg and worker-pool failures.
- Synchronize image sequence duration to narration audio.
- Add optional scene fades and Ken Burns effects.
- Support optional music mixing, SRT captions, and Whisper CLI transcription.
- Apply subscribe/notification overlay opacity correctly.
- Generate vertical Shorts with error reporting.
- Add CLI configuration, Go tests, and FFmpeg smoke checks.

## Integration status

**Implementation files are not yet committed to this branch.** The enhanced source package was generated separately and must be integrated and validated against the original branch before this PR is ready for review.

## Validation required

```sh
go mod tidy
go test ./...
go test -race ./...
go vet ./...
go build ./cmd/syncshot
```

Also test FFmpeg rendering with narration, multiple images, overlays, captions, and vertical Shorts.

# Phase 4.1 — Repeated still-image input reuse

Long narration often repeats a small image set across many scene slots. Previously the cinematic FFmpeg command opened **one input for every scene**, even when the same file appeared repeatedly.

The renderer now opens each **unique image path** once and supplies independent scene pads using FFmpeg's `split` filter. The mapping preserves first-appearance order; narration, overlays, background music, and subtitle input indices use the new input count. This substantially reduces the number of FFmpeg input demuxers for one-poster storytelling videos. Existing timelines and output defaults are unchanged.

For 45 scenes all using the same image, the image input argument count goes from 45 to 1 (the actual memory and speed impact depends on FFmpeg filter scheduling and should be benchmarked on representative videos).

Checks:
```sh
go test ./internal/cinematic
go test -short ./...
```

The integration test renders repeated images with audio ducking and a selectable subtitle stream. Compare peak RAM/CPU and rendering time before and after on a longer sample before merging; an FFmpeg split can buffer frames when consuming branches at different rates. This phase does not yet implement chunked rendering, so do not assume constant memory for arbitrarily long timelines.

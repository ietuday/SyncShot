# Phase 7.9 — Shorts sampled-frame visual-content validation

The Shorts CI fixture now decodes portrait frames at 25%, 50% and 75% of each generated clip and downsamples them to 64×64 grayscale. It records sampled mean luma and standard deviation, failing on near-black (mean <12/255) or near-flat (stddev <5/255) frames. The evidence is exported as `shorts-visual-content.json`.

This is a **synthetic-fixture-only** sanity check: valid minimal, monochrome, or intentionally dark user footage may fail these thresholds. Sampling cannot detect all frozen, cropped, letterboxed or misplaced frames, nor does it establish subject framing, subtitles readability, or perceived visual quality. Do not apply this gate unconditionally to arbitrary production footage.

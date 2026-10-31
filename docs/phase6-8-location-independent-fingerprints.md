# Phase 6.8 — Location-independent input fingerprints

The benchmark input fingerprint now uses an input root's positional index plus relative filenames, sizes and SHA-256 file digests instead of embedding absolute or working-directory-dependent source paths. Two identical input trees at different filesystem locations produce the same fingerprint if their root order matches.

Root order is significant; keep the order of paths in `SYNC_SHOT_BENCHMARK_INPUTS` consistent. File names within each root are still significant. Missing paths continue to fail; content modifications change the hash.

**Compatibility:** Fingerprints produced by earlier versions used raw source path strings and are not directly comparable to this new format. Regenerate both baseline and candidate fingerprints before comparing. This change does not automatically discover all media used by a render. Use identical input selections and complete real benchmark runs before interpreting performance comparisons.

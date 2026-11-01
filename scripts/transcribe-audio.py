#!/usr/bin/env python3
"""Optional, local speech transcription for SyncShot's Phase 9 scene planner.

Requires: pip install faster-whisper
Default CPU/int8/tiny settings are intended for low-memory laptops.
"""
import argparse
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path


def probe_duration(audio: Path) -> float:
    command = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(audio)]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    seconds = float(result.stdout.strip())
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("invalid audio duration")
    return seconds


def build_transcript(audio: Path, duration: float, segments) -> dict:
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("invalid duration")
    items = []
    previous = 0.0
    for index, segment in enumerate(segments):
        start, end = float(segment.start), float(segment.end)
        text = str(segment.text).strip()
        if (not math.isfinite(start) or not math.isfinite(end)
                or start < 0 or end <= start or end > duration + 0.25
                or start < previous - 0.01):
            raise ValueError(f"invalid segment timestamps at {index}")
        if not text:
            continue
        items.append({"start": start, "end": min(duration, end), "text": text})
        previous = end
        if len(items) > 10000:
            raise ValueError("transcript exceeds 10000 segments")
    if not items:
        raise ValueError("transcription produced no speech segments")
    return {"audio": str(audio), "duration_seconds": duration, "segments": items}


def transcribe(audio: Path, model_size: str, language: str, duration: float):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install the optional dependency: pip install faster-whisper") from exc
    model = WhisperModel(model_size, device="cpu", compute_type="int8",
                         cpu_threads=2, num_workers=1)
    result, _info = model.transcribe(str(audio),
                                    language=None if language == "auto" else language,
                                    beam_size=1, vad_filter=True)
    return build_transcript(audio, duration, result)


def save_new(destination: Path, content: dict):
    # O_EXCL prevents accidental overwriting, including a concurrently created path.
    with destination.open("x", encoding="utf-8") as stream:
        try:
            json.dump(content, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        except Exception:
            stream.close()
            destination.unlink(missing_ok=True)
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", choices=["tiny", "base", "small"], default="tiny")
    parser.add_argument("--language", choices=["auto", "hi", "en"], default="auto")
    args = parser.parse_args(argv)
    if not args.audio.is_file():
        parser.error("audio input file not found")
    if args.output.exists() or args.output.is_symlink():
        parser.error("output already exists; refusing to overwrite")
    try:
        duration = probe_duration(args.audio)
        result = transcribe(args.audio, args.model, args.language, duration)
        save_new(args.output, result)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"transcription failed: {exc}\n")
    print(f"Saved {len(result['segments'])} segments in {args.output}")


if __name__ == "__main__":
    main()

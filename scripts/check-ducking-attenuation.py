#!/usr/bin/env python3
"""Measure attenuation of an isolated music tone against a reference mix."""
import argparse
import json
import math
import re
import subprocess

def tone_amplitude(path, start, seconds, frequency):
    # Narrow-band measurement at one exact synthetic music frequency.
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
           "-ss", str(start), "-t", str(seconds), "-i", str(path),
           "-map", "0:a:0", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    import array
    samples = array.array("f")
    samples.frombytes(raw[:len(raw) // 4 * 4])
    if not samples:
        raise ValueError("no decoded audio samples")
    # Goertzel-style correlation; normalized amplitude in arbitrary units.
    real = imag = 0.0
    for i, value in enumerate(samples):
        phase = 2 * math.pi * frequency * i / 8000
        real += value * math.cos(phase)
        imag += value * math.sin(phase)
    return 2 * math.hypot(real, imag) / len(samples)

def attenuation(reference, ducked, start, seconds, frequency):
    base = tone_amplitude(reference, start, seconds, frequency)
    reduced = tone_amplitude(ducked, start, seconds, frequency)
    if base <= 1e-8 or reduced <= 0:
        raise ValueError("unmeasurable reference or rendered tone")
    db = 20 * math.log10(reduced / base)
    return {"reference_amplitude": base, "ducked_amplitude": reduced,
            "attenuation_db": db}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference")
    parser.add_argument("ducked")
    parser.add_argument("--start", type=float, default=5)
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--tone-hz", type=float, default=220)
    parser.add_argument("--minimum-reduction-db", type=float, default=2)
    args = parser.parse_args()
    data = attenuation(args.reference, args.ducked, args.start,
                       args.seconds, args.tone_hz)
    print(json.dumps(data, indent=2))
    if data["attenuation_db"] > -args.minimum_reduction_db:
        parser.exit(1, "insufficient music tone attenuation detected\n")

if __name__ == "__main__":
    main()

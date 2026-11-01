#!/usr/bin/env python3
"""Check that synthetic music volume recovers during a narration-silence gap."""
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("ducking", Path(__file__).with_name("check-ducking-attenuation.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def main(reference, ducked):
    speech = module.attenuation(reference, ducked, 2, 3, 220)
    silence = module.attenuation(reference, ducked, 8, 2, 220)
    # Require observable reduction during speech, and at least 2 dB recovery in silence.
    if speech["attenuation_db"] > -2:
        raise ValueError("music not sufficiently ducked during narration")
    if silence["attenuation_db"] - speech["attenuation_db"] < 2:
        raise ValueError("music did not recover sufficiently during narration gap")
    print(json.dumps({"during_narration_db": speech["attenuation_db"],
                      "during_silence_db": silence["attenuation_db"],
                      "recovery_db": silence["attenuation_db"] - speech["attenuation_db"]}, indent=2))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: check-ducking-recovery.py reference.mp4 ducked.mp4")
    main(sys.argv[1], sys.argv[2])

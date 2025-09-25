import os
from datetime import datetime

# Input folders
AUDIO_FOLDER = "assets/audio"
IMAGE_FOLDER = "assets/images"

# Output base
OUTPUT_BASE = "output"

# Output folders
SUBTITLE_DIR = os.path.join(OUTPUT_BASE, "subtitles")
VIDEO_DIR = os.path.join(OUTPUT_BASE, "videos")
SHORTS_DIR = os.path.join(OUTPUT_BASE, "shorts")

# Generate unique run ID (timestamp-based)
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

# Video output file
OUTPUT_VIDEO = os.path.join(VIDEO_DIR, f"output_{RUN_ID}.mp4")

# Whisper model config
# Options: "tiny", "base", "small", "medium", "large"
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")

# Subtitles
TRANSLATE_SUBS = True  # True = Hindi→English, False = keep original

# Video render settings
FPS = 24
PRESET = "medium"

# Ensure output dirs exist
for folder in [SUBTITLE_DIR, VIDEO_DIR, SHORTS_DIR]:
    os.makedirs(folder, exist_ok=True)

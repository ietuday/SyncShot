import os

# Input folders
AUDIO_FOLDER = "assets/audio"
IMAGE_FOLDER = "assets/images"

# Output base
OUTPUT_BASE = "output"

# Output folders
SUBTITLE_DIR = os.path.join(OUTPUT_BASE, "subtitles")
VIDEO_DIR = os.path.join(OUTPUT_BASE, "videos")
SHORTS_DIR = os.path.join(OUTPUT_BASE, "shorts")

# Video output file
OUTPUT_VIDEO = os.path.join(VIDEO_DIR, "output_video.mp4")

# Whisper model config
MODEL_SIZE = "base"

# Ensure output dirs exist
for folder in [SUBTITLE_DIR, VIDEO_DIR, SHORTS_DIR]:
    os.makedirs(folder, exist_ok=True)

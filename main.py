import os
import random
from config import (
    AUDIO_FOLDER, IMAGE_FOLDER,
    OUTPUT_VIDEO, SHORTS_DIR, SUBTITLE_DIR, MODEL_SIZE
)
from pipeline.video_generator import generate_video
from pipeline.shorts_creator import create_shorts

def main():
    print("🔄 SyncShot Pipeline Starting...")

    audio_files = [
        os.path.join(AUDIO_FOLDER, f)
        for f in sorted(os.listdir(AUDIO_FOLDER))
        if f.endswith(".m4a")
    ]
    if not audio_files:
        raise FileNotFoundError("No .m4a audio found.")
    audio_file = audio_files[0]

    image_files = [
        os.path.join(IMAGE_FOLDER, f)
        for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not image_files:
        raise FileNotFoundError("No image files found.")
    random.shuffle(image_files)

    generate_video(audio_file, image_files, OUTPUT_VIDEO, subtitle_dir=SUBTITLE_DIR, model_size=MODEL_SIZE)

    subtitled_video = os.path.join(os.path.dirname(OUTPUT_VIDEO), "output_video_subtitled.mp4")
    create_shorts(subtitled_video, shorts_dir=SHORTS_DIR)

if __name__ == "__main__":
    main()

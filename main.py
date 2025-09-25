import os
from config import (
    AUDIO_FOLDER, IMAGE_FOLDER,
    OUTPUT_VIDEO, SHORTS_DIR, SUBTITLE_DIR,
    MODEL_SIZE, TRANSLATE_SUBS, FPS, PRESET
)
from pipeline.video_generator import generate_video
from pipeline.shorts_creator import create_shorts


def main():
    print("🔄 SyncShot Pipeline Starting...")

    # 🎵 Collect audio
    audio_files = [
        os.path.join(AUDIO_FOLDER, f)
        for f in sorted(os.listdir(AUDIO_FOLDER))
        if f.endswith(".mp4") or f.endswith(".m4a")
    ]
    if not audio_files:
        raise FileNotFoundError(f"No .mp4 or .m4a audio found in {AUDIO_FOLDER}")
    audio_file = audio_files[0]

    # 🖼️ Collect images
    image_files = [
        os.path.join(IMAGE_FOLDER, f)
        for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not image_files:
        raise FileNotFoundError(f"No image files found in {IMAGE_FOLDER}")

    # 🎬 Generate video with subtitles
    subtitled_video = generate_video(
        audio_file,
        image_files,
        OUTPUT_VIDEO,
        subtitle_dir=SUBTITLE_DIR,
        model_size=MODEL_SIZE,
        fps=FPS,
        preset=PRESET,
        translate_subs=TRANSLATE_SUBS
    )

    # ✂️ Create shorts
    create_shorts(subtitled_video, shorts_dir=SHORTS_DIR)


if __name__ == "__main__":
    main()

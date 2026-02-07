import logging
import os
from pathlib import Path
from config import (
    AUDIO_FOLDER, IMAGE_FOLDER,
    OUTPUT_VIDEO, SHORTS_DIR, SUBTITLE_DIR,
    MODEL_SIZE, TRANSLATE_SUBS, FPS, PRESET, VIDEO_DIR,
    # add LOG_LEVEL / LOG_FILE in config if you want
)
from utils.clear_output import SUB_EXTS, VIDEO_EXTS, clear_dir, delete_file_if_exists, delete_output_subtitled
from utils.logger import setup_logging
from pipeline.video_generator import generate_video
from pipeline.shorts_creator import create_shorts

logger = logging.getLogger(__name__)

def main():
    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_file=os.getenv("LOG_FILE"))
    # ✅ CLEAR OUTPUTS FIRST (before doing anything else)
    try:
        # ensure dirs exist (so later steps won't fail)
        Path(SHORTS_DIR).mkdir(parents=True, exist_ok=True)
        Path(SUBTITLE_DIR).mkdir(parents=True, exist_ok=True)
        Path(os.path.dirname(OUTPUT_VIDEO) or ".").mkdir(parents=True, exist_ok=True)

        logger.info("Clearing output folders...")

        # clear shorts
        clear_dir(SHORTS_DIR, allowed_exts=VIDEO_EXTS)

        # clear subtitles
        clear_dir(SUBTITLE_DIR, allowed_exts=SUB_EXTS)

        # delete final output video file (OUTPUT_VIDEO is a file path in your code)
        delete_file_if_exists(OUTPUT_VIDEO)

        delete_output_subtitled(os.path.join(VIDEO_DIR, f"output_subtitled.mp4"))

        logger.info("Output folders cleared ✅")
    except Exception as e:
        logger.exception("Failed while clearing outputs: %s", e)
        raise


    logger.info("SyncShot Pipeline Starting...")

    # 🎵 Collect audio
    audio_files = [
        os.path.join(AUDIO_FOLDER, f)
        for f in sorted(os.listdir(AUDIO_FOLDER))
        if f.lower().endswith((".mp4", ".m4a"))
    ]
    if not audio_files:
        logger.error("No .mp4 or .m4a audio found in %s", AUDIO_FOLDER)
        raise FileNotFoundError(f"No .mp4 or .m4a audio found in {AUDIO_FOLDER}")

    audio_file = audio_files[0]
    logger.info("Using audio: %s", os.path.basename(audio_file))

    # 🖼️ Collect images
    image_files = [
        os.path.join(IMAGE_FOLDER, f)
        for f in sorted(os.listdir(IMAGE_FOLDER))
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not image_files:
        logger.error("No image files found in %s", IMAGE_FOLDER)
        raise FileNotFoundError(f"No image files found in {IMAGE_FOLDER}")
    logger.info("Found %d images", len(image_files))

    # 🎬 Generate video with subtitles
    logger.info("Generating video (fps=%s preset=%s model=%s translate=%s)...",
                FPS, PRESET, MODEL_SIZE, TRANSLATE_SUBS)

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

    logger.info("Video generated: %s", subtitled_video)

    # ✂️ Create shorts
    logger.info("Creating shorts into: %s", SHORTS_DIR)
    #create_shorts(subtitled_video, shorts_dir=SHORTS_DIR)
    create_shorts(
        subtitled_video,
        shorts_dir=SHORTS_DIR,
        fps=FPS,
        preset=PRESET,
        mode="start",     # ✅ start -> end
        short_len=50,     # ✅ 50 sec each
        count=None,       # ✅ None = generate all possible 50s shorts till video end
        layout="fit_bg",       # ✅ recommended
        anchor_x="center",
        anchor_y="center",
    )

    logger.info("SyncShot Pipeline Completed ✅")

if __name__ == "__main__":
    main()

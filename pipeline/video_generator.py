import logging
import os
import uuid
import subprocess
from tqdm import tqdm
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips

from .image_utils import resize_image
from .subtitle_utils import transcribe_audio_to_ass

logger = logging.getLogger(__name__)


def _ffmpeg_ass_filter(ass_path: str) -> str:
    """
    Build a safe ffmpeg ass= filter value.
    FFmpeg filters treat ':' as option separator; backslashes and colons in paths
    (especially Windows) must be escaped.

    Works cross-platform.
    """
    p = os.path.abspath(ass_path)

    # Escape for ffmpeg filter parsing:
    # - backslash -> double backslash
    # - colon -> \:
    # - single quote -> '\''
    p = p.replace("\\", "\\\\")
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")

    # Wrap in single quotes so spaces are safe
    return f"ass='{p}'"


def burn_subtitles(video_path: str, ass_path: str, output_path_with_subs: str, strict: bool = True) -> str:
    logger.info("Burning subtitles video=%s ass=%s out=%s", video_path, ass_path, output_path_with_subs)

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.isfile(ass_path):
        raise FileNotFoundError(f"ASS not found: {ass_path}")

    os.makedirs(os.path.dirname(output_path_with_subs) or ".", exist_ok=True)

    vf = _ffmpeg_ass_filter(ass_path)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:a", "copy",
        output_path_with_subs,
    ]

    logger.debug("FFmpeg cmd: %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(output_path_with_subs):
        msg = (
            f"FFmpeg subtitle burn failed (code={result.returncode}).\n"
            f"STDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
        )
        if strict:
            logger.error(msg)
            raise RuntimeError(msg)
        else:
            logger.warning(msg)
            return video_path

    logger.info("Subtitle-burned video saved: %s", output_path_with_subs)
    return output_path_with_subs


def generate_video(
    audio_path: str,
    image_paths: list[str],
    output_path: str,
    subtitle_dir: str,
    model_size: str = "base",
    fps: int = 24,
    preset: str = "medium",
    translate_subs: bool = True,
) -> str:
    """
    Generate a video with audio + image slideshow, add subtitles (transcribe/translate),
    then burn subtitles with ffmpeg.
    """
    audio = None
    video = None
    clips: list[ImageClip] = []

    try:
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio not found: {audio_path}")
        if not image_paths:
            raise ValueError("image_paths is empty")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        os.makedirs(subtitle_dir, exist_ok=True)

        # unique subtitle file
        ass_output = os.path.join(subtitle_dir, f"subs_{uuid.uuid4().hex}.ass")

        logger.info(
            "generate_video start audio=%s images=%d out=%s fps=%d preset=%s model=%s translate=%s",
            audio_path, len(image_paths), output_path, fps, preset, model_size, translate_subs
        )

        # Generate subtitles
        transcribe_audio_to_ass(
            audio_path=audio_path,
            ass_output=ass_output,
            model_size=model_size,
            translate=translate_subs
        )
        logger.info("ASS generated: %s", ass_output)

        # prepare audio & images
        audio = AudioFileClip(audio_path)
        duration = float(audio.duration or 0.0)
        if duration <= 0:
            raise ValueError(f"Invalid audio duration: {duration}")

        image_duration = duration / len(image_paths)
        logger.info("Audio duration=%.2fs -> per-image duration=%.3fs", duration, image_duration)

        # Build image clips
        for img_path in tqdm(image_paths, desc="🖼️ Processing Images"):
            try:
                img_array = resize_image(img_path)
                if img_array is None:
                    logger.warning("Skipping invalid image: %s", img_path)
                    continue
                clips.append(ImageClip(img_array, duration=image_duration))
            except Exception:
                logger.exception("Failed processing image: %s", img_path)

        if not clips:
            raise ValueError("No valid images to create video.")

        logger.info("Creating slideshow clips=%d", len(clips))

        video = concatenate_videoclips(clips, method="compose")
        video = CompositeVideoClip([video])
        video.audio = audio

        logger.info("Writing base video: %s", output_path)
        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=fps,
            preset=preset,
            threads=os.cpu_count() or 4,
            logger=None,  # prevents MoviePy console spam; your logs stay clean
        )

        output_with_subs = os.path.splitext(output_path)[0] + "_subtitled.mp4"
        final_path = burn_subtitles(output_path, ass_output, output_with_subs, strict=True)

        logger.info("generate_video done final=%s", final_path)
        return final_path

    except Exception:
        logger.exception("generate_video failed audio=%s out=%s", audio_path, output_path)
        raise

    finally:
        # Cleanup
        try:
            if audio:
                audio.close()
        except Exception:
            logger.debug("Audio close failed", exc_info=True)

        try:
            if video:
                video.close()
        except Exception:
            logger.debug("Video close failed", exc_info=True)

        for c in clips:
            try:
                c.close()
            except Exception:
                pass

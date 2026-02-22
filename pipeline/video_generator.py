import logging
import os
import uuid
import subprocess
import random
from typing import List, Optional

from tqdm import tqdm

# MoviePy (works across v1/v2 with the compat helpers below)
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip
from moviepy import vfx

from .image_utils import resize_image
from .subtitle_utils import transcribe_audio_to_ass

logger = logging.getLogger(__name__)

# -----------------------------
# MoviePy version-compat helpers
# -----------------------------
def _set_duration(clip, duration: float):
    return clip.with_duration(duration) if hasattr(clip, "with_duration") else clip.set_duration(duration)

def _set_start(clip, start: float):
    return clip.with_start(start) if hasattr(clip, "with_start") else clip.set_start(start)

def _resize_dynamic(clip, zoom_fn):
    # v2+ prefers effects classes
    if hasattr(clip, "with_effects") and hasattr(vfx, "Resize"):
        return clip.with_effects([vfx.Resize(zoom_fn)])
    # v1 uses fx(function)
    if hasattr(clip, "fx") and hasattr(vfx, "resize"):
        return clip.fx(vfx.resize, zoom_fn)
    # fallback
    if hasattr(clip, "resize"):
        return clip.resize(zoom_fn)
    return clip

def _crossfadein(clip, t: float):
    # v1
    if hasattr(clip, "crossfadein"):
        return clip.crossfadein(t)
    # v2+ (if available)
    if hasattr(clip, "with_effects") and hasattr(vfx, "CrossFadeIn"):
        return clip.with_effects([vfx.CrossFadeIn(t)])
    return clip

def _crossfadeout(clip, t: float):
    # v1
    if hasattr(clip, "crossfadeout"):
        return clip.crossfadeout(t)
    # v2+ (if available)
    if hasattr(clip, "with_effects") and hasattr(vfx, "CrossFadeOut"):
        return clip.with_effects([vfx.CrossFadeOut(t)])
    return clip


# -----------------------------
# Animated clip (Ken Burns)
# -----------------------------
def make_animated_image_clip(img_array, duration: float, zoom_max: float = 0.06) -> ImageClip:
    """
    Subtle zoom in/out per image (Ken Burns).
    This is safe across MoviePy v1/v2 using compat resize helper.
    """
    clip = ImageClip(img_array)
    clip = _set_duration(clip, duration)

    zoom_in = random.choice([True, False])

    def zoom_factor(t: float) -> float:
        d = max(duration, 0.001)
        p = t / d
        if zoom_in:
            return 1.0 + (zoom_max * p)          # 1 -> 1+zoom
        return 1.0 + (zoom_max * (1.0 - p))      # 1+zoom -> 1

    clip = _resize_dynamic(clip, zoom_factor)
    return clip


# -----------------------------
# Crossfade slideshow builder
# -----------------------------
def build_crossfade_slideshow(clips: List[ImageClip], fade: float = 0.6) -> CompositeVideoClip:
    """
    Overlap each next clip by `fade` seconds and crossfade.
    Returns a CompositeVideoClip timeline.
    """
    if not clips:
        raise ValueError("No clips to build slideshow")

    # Ensure fade is sane relative to clip durations
    min_dur = min(float(getattr(c, "duration", 0) or 0) for c in clips)
    if fade <= 0:
        fade = 0.0
    elif min_dur > 0 and fade >= (min_dur * 0.8):
        # keep fade smaller than clip duration
        fade = max(0.05, min_dur * 0.3)

    timeline = []
    t = 0.0

    # First clip starts at 0
    first = clips[0]
    timeline.append(_set_start(first, t))
    t += float(first.duration or 0.0)

    for c in clips[1:]:
        # start next clip `fade` seconds before current timeline time (overlap)
        t = max(0.0, t - fade)

        # fade out previous clip
        timeline[-1] = _crossfadeout(timeline[-1], fade)

        # fade in current clip
        c2 = _crossfadein(c, fade)
        c2 = _set_start(c2, t)
        timeline.append(c2)

        t += float(c.duration or 0.0)

    return CompositeVideoClip(timeline)


# -----------------------------
# Subtitles burn using ffmpeg
# -----------------------------
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
    # - single quote -> \'
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


# -----------------------------
# Main API
# -----------------------------
def generate_video(
    audio_path: str,
    image_paths: list[str],
    output_path: str,
    subtitle_dir: str,
    model_size: str = "base",
    fps: int = 24,
    preset: str = "medium",
    translate_subs: bool = True,
    fade_duration: float = 0.6,     # ✅ crossfade seconds
    zoom_max: float = 0.06,         # ✅ ken burns max zoom (0.04–0.08 sweet spot)
) -> str:
    """
    Generate a video with:
    - audio + image slideshow
    - subtle image zoom animation
    - crossfade transitions between images
    - subtitles generated as .ass and burned with ffmpeg
    """
    audio: Optional[AudioFileClip] = None
    video: Optional[CompositeVideoClip] = None
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
            "generate_video start audio=%s images=%d out=%s fps=%d preset=%s model=%s translate=%s fade=%.2fs zoom=%.2f%%",
            audio_path, len(image_paths), output_path, fps, preset, model_size, translate_subs, fade_duration, zoom_max * 100
        )

        # Generate subtitles
        transcribe_audio_to_ass(
            audio_path=audio_path,
            ass_output=ass_output,
            model_size=model_size,
            translate=translate_subs
        )
        logger.info("ASS generated: %s", ass_output)

        # prepare audio
        audio = AudioFileClip(audio_path)
        duration = float(audio.duration or 0.0)
        if duration <= 0:
            raise ValueError(f"Invalid audio duration: {duration}")

        image_duration = duration / len(image_paths)
        logger.info("Audio duration=%.2fs -> per-image duration=%.3fs", duration, image_duration)

        # If image_duration is too small, reduce fade automatically
        if image_duration <= 0.8:
            # avoid fade dominating clip time
            fade_duration = min(fade_duration, max(0.1, image_duration * 0.25))

        # Build animated image clips
        for img_path in tqdm(image_paths, desc="🖼️ Processing Images"):
            try:
                img_array = resize_image(img_path)
                if img_array is None:
                    logger.warning("Skipping invalid image: %s", img_path)
                    continue

                animated = make_animated_image_clip(
                    img_array=img_array,
                    duration=image_duration,
                    zoom_max=zoom_max,
                )
                clips.append(animated)

            except Exception:
                logger.exception("Failed processing image: %s", img_path)

        if not clips:
            raise ValueError("No valid images to create video.")

        logger.info("Creating slideshow clips=%d fade=%.2fs", len(clips), fade_duration)

        # ✅ Crossfade slideshow instead of hard cuts
        video = build_crossfade_slideshow(clips, fade=fade_duration)
        video.audio = audio

        logger.info("Writing base video: %s", output_path)
        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=fps,
            preset=preset,
            threads=os.cpu_count() or 4,
            logger=None,  # keeps logs clean
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

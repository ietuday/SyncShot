import logging
import os
from moviepy import VideoFileClip

logger = logging.getLogger(__name__)

def _to_vertical_9_16(clip: VideoFileClip, out_w=1080, out_h=1920) -> VideoFileClip:
    """
    Convert any clip to vertical 9:16 (1080x1920) by:
      1) scaling so height matches out_h (keeps aspect ratio)
      2) center-cropping width to out_w
    This avoids stretching/distortion.
    """
    # scale to target height first (keeps aspect ratio)
    scaled = clip.resized(height=out_h)

    # if width is still smaller (rare), scale by width instead
    if scaled.w < out_w:
        scaled = clip.resized(width=out_w)

    x_center = scaled.w / 2
    y_center = scaled.h / 2
    vertical = scaled.cropped(
        x_center=x_center,
        y_center=y_center,
        width=out_w,
        height=out_h
    )
    return vertical


def create_shorts(video_path: str, shorts_dir: str = "shorts", fps: int = 30):
    os.makedirs(shorts_dir, exist_ok=True)

    shorts = [
        ("short1.mp4", 10, 25),
        ("short2.mp4", 30, 45),
        ("short3.mp4", 50, 65),
    ]

    logger.info("create_shorts started video=%s out_dir=%s", video_path, shorts_dir)

    if not os.path.isfile(video_path):
        logger.error("Input video not found: %s", video_path)
        raise FileNotFoundError(video_path)

    # Use context manager so resources are always released
    with VideoFileClip(video_path) as clip:
        duration = float(clip.duration or 0.0)
        logger.info("Loaded video duration=%.2fs size=%dx%d fps=%s", duration, clip.w, clip.h, getattr(clip, "fps", None))

        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}")

        vertical_clip = _to_vertical_9_16(clip, out_w=1080, out_h=1920)
        logger.info("Prepared vertical clip size=%dx%d", vertical_clip.w, vertical_clip.h)

        for filename, start, end in shorts:
            # clamp to duration
            s = max(0.0, float(start))
            e = min(duration, float(end))

            if e <= s:
                logger.warning("Skipping %s (invalid range start=%.2f end=%.2f)", filename, s, e)
                continue

            short_path = os.path.join(shorts_dir, filename)
            logger.info("Rendering %s range=%.2f..%.2f -> %s", filename, s, e, short_path)

            try:
                sub = vertical_clip.subclipped(s, e)

                # write file
                sub.write_videofile(
                    short_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=fps,
                    threads=os.cpu_count() or 4,
                    preset="medium",
                    logger=None,  # prevents MoviePy from spamming; your logger will be used
                )

                logger.info("Rendered %s OK", short_path)

            except Exception:
                logger.exception("Failed rendering %s", filename)
                # continue with next short rather than killing the whole pipeline

    logger.info("create_shorts completed")

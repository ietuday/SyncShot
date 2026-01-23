import logging
import os
from moviepy import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

logger = logging.getLogger(__name__)


def _fit_vertical_9_16(clip: VideoFileClip, out_w: int = 1080, out_h: int = 1920) -> VideoFileClip:
    """
    FIT (no crop): scale the clip to fit fully inside 1080x1920 (9:16),
    then pad the remaining area (black bars) so NOTHING is cut.
    """
    # MoviePy v1/v2 compatibility
    resize_fn = getattr(clip, "resize", None) or getattr(clip, "resized", None)
    if not resize_fn:
        raise AttributeError("MoviePy clip has neither resize nor resized")

    # Scale so both dimensions fit inside target (contain)
    scale = min(out_w / clip.w, out_h / clip.h)
    new_w = max(2, int(clip.w * scale))
    new_h = max(2, int(clip.h * scale))

    # width-based resize keeps aspect ratio (height follows)
    fitted = resize_fn(width=new_w)

    # Center position (MoviePy v1/v2 compatibility)
    pos_fn = getattr(fitted, "set_position", None) or getattr(fitted, "with_position", None)
    if not pos_fn:
        raise AttributeError("MoviePy clip has neither set_position nor with_position")
    fitted = pos_fn(("center", "center"))

    # Create 1080x1920 canvas and place fitted clip in center
    canvas = CompositeVideoClip([fitted], size=(out_w, out_h))

    # Background color for padding (MoviePy v1/v2 compatibility)
    bg_fn = getattr(canvas, "set_bg_color", None) or getattr(canvas, "with_bg_color", None)
    if bg_fn:
        canvas = bg_fn((0, 0, 0))

    return canvas


def _subclip(clip, start: float, end: float):
    # MoviePy v1/v2 compatibility
    fn = getattr(clip, "subclip", None) or getattr(clip, "subclipped", None)
    if not fn:
        raise AttributeError("MoviePy clip has neither subclip nor subclipped")
    return fn(start, end)


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
        logger.info(
            "Loaded video duration=%.2fs size=%dx%d fps=%s",
            duration,
            clip.w,
            clip.h,
            getattr(clip, "fps", None),
        )

        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}")

        # ✅ FIT into 9:16 without cropping
        vertical_clip = _fit_vertical_9_16(clip, out_w=1080, out_h=1920)
        logger.info("Prepared vertical (fit) clip size=%dx%d", vertical_clip.w, vertical_clip.h)

        for filename, start, end in shorts:
            s = max(0.0, float(start))
            e = min(duration, float(end))

            if e <= s:
                logger.warning("Skipping %s (invalid range start=%.2f end=%.2f)", filename, s, e)
                continue

            short_path = os.path.join(shorts_dir, filename)
            logger.info("Rendering %s range=%.2f..%.2f -> %s", filename, s, e, short_path)

            sub = None
            try:
                sub = _subclip(vertical_clip, s, e)

                sub.write_videofile(
                    short_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=fps,
                    threads=os.cpu_count() or 4,
                    preset="medium",
                    ffmpeg_params=["-movflags", "+faststart"],
                    logger=None,  # prevent MoviePy spam; rely on your logger
                )

                logger.info("Rendered %s OK", short_path)

            except Exception:
                logger.exception("Failed rendering %s", filename)
                # continue with next short rather than killing the whole pipeline
            finally:
                # Free resources ASAP
                try:
                    if sub is not None:
                        sub.close()
                except Exception:
                    pass

    logger.info("create_shorts completed")

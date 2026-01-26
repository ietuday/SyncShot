# pipeline/shorts_creator.py

import logging
import os
from typing import List, Tuple, Optional

from moviepy import VideoFileClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

logger = logging.getLogger(__name__)


def _resize_clip(clip, *, width: Optional[int] = None, height: Optional[int] = None):
    """
    MoviePy v1/v2 safe resize:
    - v1: resize(width=..)/resize(height=..)
    - v2: resized(width=..)/resized(height=..)
    """
    fn = getattr(clip, "resize", None) or getattr(clip, "resized", None)
    if not fn:
        raise AttributeError("MoviePy clip has neither resize nor resized")

    if width is not None:
        return fn(width=max(2, int(width)))
    if height is not None:
        return fn(height=max(2, int(height)))

    raise ValueError("Either width or height must be provided to _resize_clip")


def _set_position(clip, pos):
    fn = getattr(clip, "set_position", None) or getattr(clip, "with_position", None)
    if not fn:
        raise AttributeError("MoviePy clip has neither set_position nor with_position")
    return fn(pos)


def _set_bg_color(clip, color):
    fn = getattr(clip, "set_bg_color", None) or getattr(clip, "with_bg_color", None)
    if fn:
        return fn(color)
    return clip


def _subclip(clip, start: float, end: float):
    fn = getattr(clip, "subclip", None) or getattr(clip, "subclipped", None)
    if not fn:
        raise AttributeError("MoviePy clip has neither subclip nor subclipped")
    return fn(start, end)


def _anchor_offset(container: int, content: int, anchor: str) -> int:
    """
    Compute x/y offset for content inside container.
    anchor: "left"/"center"/"right" (for x), "top"/"center"/"bottom" (for y)
    """
    if anchor in ("left", "top"):
        return 0
    if anchor in ("right", "bottom"):
        return container - content
    # center
    return (container - content) // 2


def _fit_vertical_9_16(
    clip: VideoFileClip,
    out_w: int = 1080,
    out_h: int = 1920,
    bg_color=(0, 0, 0),
) -> VideoFileClip:
    """
    FIT (no crop): keep whole frame, black bars possible.
    """
    scale = min(out_w / clip.w, out_h / clip.h)
    new_w = max(2, int(round(clip.w * scale)))

    fitted = _resize_clip(clip, width=new_w)
    fitted = _set_position(fitted, ("center", "center"))

    canvas = CompositeVideoClip([fitted], size=(out_w, out_h))
    canvas = _set_bg_color(canvas, bg_color)
    return canvas


def _fill_vertical_9_16(
    clip: VideoFileClip,
    out_w: int = 1080,
    out_h: int = 1920,
    anchor_x: str = "center",  # left/center/right
    anchor_y: str = "center",  # top/center/bottom
    bg_color=(0, 0, 0),
) -> VideoFileClip:
    """
    FILL (cropping): cover full 9:16, no black bars.
    Uses CompositeVideoClip clipping (no crop() needed).
    """
    cover_scale = max(out_w / clip.w, out_h / clip.h)

    target_w = max(2, int(round(clip.w * cover_scale)))
    scaled = _resize_clip(clip, width=target_w)

    sw = int(getattr(scaled, "w", 0) or 0)
    sh = int(getattr(scaled, "h", 0) or 0)
    if sw <= 0 or sh <= 0:
        raise ValueError(f"Invalid scaled size w={sw} h={sh}")

    x = _anchor_offset(out_w, sw, anchor_x)
    y = _anchor_offset(out_h, sh, anchor_y)

    placed = _set_position(scaled, (x, y))
    canvas = CompositeVideoClip([placed], size=(out_w, out_h))
    canvas = _set_bg_color(canvas, bg_color)
    return canvas


def _fit_with_background(
    clip: VideoFileClip,
    out_w: int = 1080,
    out_h: int = 1920,
    anchor_x: str = "center",
    anchor_y: str = "center",
    dim: float = 0.35,
) -> VideoFileClip:
    """
    BEST for Shorts without losing content:
    - background: fill (cropped) + dim
    - foreground: fit (no crop)
    Result: no black bars + no important cutting
    """
    # background (fill)
    bg = _fill_vertical_9_16(
        clip,
        out_w=out_w,
        out_h=out_h,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
    )

    # dim background (works in v1/v2 if fx exists)
    try:
        from moviepy.video.fx.all import colorx
        bg = bg.fx(colorx, dim)
    except Exception:
        # if fx not available, ignore
        pass

    # foreground (fit)
    fg = _fit_vertical_9_16(clip, out_w=out_w, out_h=out_h, bg_color=(0, 0, 0))
    # fg already has black bars on its own canvas; we want ONLY the fitted video,
    # so rebuild fg as a single fitted layer:
    scale = min(out_w / clip.w, out_h / clip.h)
    new_w = max(2, int(round(clip.w * scale)))
    fitted = _resize_clip(clip, width=new_w)
    fitted = _set_position(fitted, ("center", "center"))

    comp = CompositeVideoClip([bg, fitted], size=(out_w, out_h))
    return comp


def _build_start_ranges(duration: float, short_len: float, count: Optional[int], gap: float) -> List[Tuple[float, float]]:
    ranges: List[Tuple[float, float]] = []
    start = 0.0
    i = 0
    while start < duration:
        end = min(duration, start + float(short_len))
        if end > start:
            ranges.append((start, end))
        start = end + float(gap)
        i += 1
        if count is not None and i >= int(count):
            break
    return ranges


def create_shorts(
    video_path: str,
    shorts_dir: str = "shorts",
    fps: int = 30,
    preset: str = "medium",
    out_w: int = 1080,
    out_h: int = 1920,
    mode: str = "start",          # "start" / "end" / "manual"
    short_len: float = 30.0,
    count: Optional[int] = None,
    gap: float = 0.0,
    layout: str = "fit_bg",       # ✅ "fit_bg" recommended, or "fill" / "fit"
    anchor_x: str = "center",     # left/center/right
    anchor_y: str = "center",     # top/center/bottom
    manual_ranges: Optional[List[Tuple[float, float]]] = None,
):
    os.makedirs(shorts_dir, exist_ok=True)

    logger.info(
        "create_shorts started video=%s out_dir=%s mode=%s short_len=%s count=%s layout=%s anchor_x=%s anchor_y=%s",
        video_path, shorts_dir, mode, short_len, count, layout, anchor_x, anchor_y
    )

    if not os.path.isfile(video_path):
        raise FileNotFoundError(video_path)

    with VideoFileClip(video_path) as clip:
        duration = float(clip.duration or 0.0)
        logger.info(
            "Loaded video duration=%.2fs size=%dx%d fps=%s",
            duration, clip.w, clip.h, getattr(clip, "fps", None),
        )
        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}")

        # Build vertical base clip
        layout_l = layout.lower().strip()
        if layout_l == "fit":
            vertical = _fit_vertical_9_16(clip, out_w=out_w, out_h=out_h)
        elif layout_l == "fill":
            vertical = _fill_vertical_9_16(
                clip, out_w=out_w, out_h=out_h, anchor_x=anchor_x, anchor_y=anchor_y
            )
        else:
            # default best
            vertical = _fit_with_background(
                clip, out_w=out_w, out_h=out_h, anchor_x=anchor_x, anchor_y=anchor_y
            )

        logger.info("Prepared vertical clip size=%dx%d", vertical.w, vertical.h)

        # Ranges (start mode only here)
        if mode == "manual":
            ranges = manual_ranges or []
        else:
            ranges = _build_start_ranges(duration, short_len=short_len, count=count, gap=gap)

        if not ranges:
            logger.warning("No valid ranges generated. Nothing to render.")
            return

        logger.info("Short ranges=%s", ranges)

        for i, (start, end) in enumerate(ranges, start=1):
            s = max(0.0, float(start))
            e = min(duration, float(end))
            if e <= s:
                logger.warning("Skipping short%d (invalid range start=%.2f end=%.2f)", i, s, e)
                continue

            out_path = os.path.join(shorts_dir, f"short{i}.mp4")
            logger.info("Rendering short%d range=%.2f..%.2f -> %s", i, s, e, out_path)

            sub = None
            try:
                sub = _subclip(vertical, s, e)
                sub.write_videofile(
                    out_path,
                    codec="libx264",
                    audio_codec="aac",
                    fps=fps,
                    threads=os.cpu_count() or 4,
                    preset=preset,
                    ffmpeg_params=["-movflags", "+faststart"],
                    logger=None,
                )
                logger.info("Rendered %s OK", out_path)
            except Exception:
                logger.exception("Failed rendering short%d", i)
            finally:
                try:
                    if sub is not None:
                        sub.close()
                except Exception:
                    pass

    logger.info("create_shorts completed")

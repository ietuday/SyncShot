from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}
SUB_EXTS = {".srt", ".vtt", ".ass"}

def delete_output_subtitled(video_output_path: str) -> None:
    """
    Deletes the file pointed by OUTPUT_VIDEO (e.g. output_subtitled.mp4).
    """
    p = Path(video_output_path)
    if p.exists() and p.is_file():
        p.unlink(missing_ok=True)
        logger.info("Deleted: %s", p)
    else:
        logger.info("Not found (skip): %s", p)

def clear_dir(dir_path: str, allowed_exts: set[str] | None = None) -> None:
    """
    Deletes files in a directory (recursively).
    If allowed_exts is provided, deletes only those file extensions.
    Removes empty subfolders after cleanup.
    """
    p = Path(dir_path)
    if not p.exists():
        return
    if not p.is_dir():
        raise ValueError(f"Not a directory: {p}")

    # Delete matching files
    for f in p.rglob("*"):
        if f.is_file():
            if allowed_exts is None or f.suffix.lower() in allowed_exts:
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    logger.exception("Failed to delete file: %s", f)

    # Remove empty dirs bottom-up
    for d in sorted([d for d in p.rglob("*") if d.is_dir()], key=lambda x: len(str(x)), reverse=True):
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass


def delete_file_if_exists(file_path: str) -> None:
    p = Path(file_path)
    if p.exists() and p.is_file():
        try:
            p.unlink(missing_ok=True)
        except Exception:
            logger.exception("Failed to delete file: %s", p)


def clear_outputs(shorts_dir: str, subtitle_dir: str, output_video_path: str) -> None:
    """
    Clears:
    - shorts_dir: only video files
    - subtitle_dir: only subtitle files
    - output_video_path: deletes the final output video file
    """
    logger.info("Clearing outputs... shorts=%s subs=%s out=%s", shorts_dir, subtitle_dir, output_video_path)

    Path(shorts_dir).mkdir(parents=True, exist_ok=True)
    Path(subtitle_dir).mkdir(parents=True, exist_ok=True)
    Path(Path(output_video_path).parent or ".").mkdir(parents=True, exist_ok=True)

    clear_dir(shorts_dir, allowed_exts=VIDEO_EXTS)
    clear_dir(subtitle_dir, allowed_exts=SUB_EXTS)
    delete_file_if_exists(output_video_path)

    logger.info("Outputs cleared ✅")

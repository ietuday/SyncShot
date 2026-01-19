import logging
import numpy as np
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

def resize_image(image_path: str, target_size=(1920, 1080)) -> np.ndarray | None:
    """
    Resize an image to fill target_size while preserving aspect ratio,
    then center-crop/pad with black bars (letterbox) by pasting onto canvas.

    Returns:
        np.ndarray (H, W, 3) in RGB, or None on failure.
    """
    try:
        # Open + handle EXIF rotation (common on phone photos)
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        if img.width <= 0 or img.height <= 0:
            raise ValueError(f"Invalid image dimensions: {img.size}")

        # Convert to RGB (handles RGBA/P/etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]

        if img_ratio > target_ratio:
            # Wider than target: match height, expand width
            new_height = target_size[1]
            new_width = int(round(new_height * img_ratio))
        else:
            # Taller than target: match width, expand height
            new_width = target_size[0]
            new_height = int(round(new_width / img_ratio))

        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Create canvas and paste centered (letterbox / pillarbox)
        canvas = Image.new("RGB", target_size, (0, 0, 0))
        offset_x = (target_size[0] - new_width) // 2
        offset_y = (target_size[1] - new_height) // 2
        canvas.paste(img_resized, (offset_x, offset_y))

        logger.debug(
            "resize_image success path=%s original=%s resized=%s target=%s offset=(%d,%d)",
            image_path, img.size, img_resized.size, target_size, offset_x, offset_y
        )

        return np.asarray(canvas)

    except Exception:
        # exception() logs stacktrace automatically
        logger.exception("resize_image failed path=%s target=%s", image_path, target_size)
        return None

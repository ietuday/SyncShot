import os
import numpy as np
from PIL import Image

def resize_image(image_path, target_size=(1920, 1080)):
    try:
        img = Image.open(image_path)
        img_ratio = img.width / img.height
        target_ratio = target_size[0] / target_size[1]

        if img_ratio > target_ratio:
            new_height = target_size[1]
            new_width = int(new_height * img_ratio)
        else:
            new_width = target_size[0]
            new_height = int(new_width / img_ratio)

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        new_img = Image.new('RGB', target_size, (0, 0, 0))
        offset = ((target_size[0] - new_width) // 2, (target_size[1] - new_height) // 2)
        new_img.paste(img, offset)

        return np.array(new_img)
    except Exception as e:
        print(f"❌ Error processing image {image_path}: {str(e)}")
        return None

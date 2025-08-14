"""Image preprocessing utilities.

Preprocessing receipt images can improve OCR and model
performance. The functions in this module perform basic
transformations such as converting to grayscale and resizing to
ensure the image fits within a reasonable size. Pillow is used as
the imaging backend. If Pillow is not installed these functions
will simply return the original image data.
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore


def preprocess_image(image_data: bytes, max_size: int = 1024) -> bytes:
    """Preprocess an image for receipt extraction.

    This function attempts to open the image, convert it to
    grayscale and resize the longest edge to ``max_size`` pixels while
    maintaining aspect ratio. If Pillow is unavailable it returns
    the original bytes unchanged.

    :param image_data: Raw image bytes
    :param max_size: Maximum size of the longest edge in pixels
    :returns: Processed image bytes in JPEG format
    """
    if Image is None:
        # Pillow not available; return original data
        return image_data
    try:
        with Image.open(BytesIO(image_data)) as img:
            # Convert to RGB then to grayscale
            img = img.convert("L")  # grayscale
            # Resize while preserving aspect ratio
            width, height = img.size
            max_dim = max(width, height)
            if max_dim > max_size:
                scale = max_size / float(max_dim)
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size)
            # Save to JPEG in memory
            buf = BytesIO()
            img.save(buf, format="JPEG")
            return buf.getvalue()
    except Exception:
        # If anything goes wrong return original data
        return image_data
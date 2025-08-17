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
    import fitz  # PyMuPDF for PDF rasterization
except Exception:  # pragma: no cover
    fitz = None  # type: ignore

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


def generate_thumbnail(data: bytes, filename: str, max_size: int = 480) -> Optional[bytes]:
    """Generate a small JPEG thumbnail for images or PDFs.

    - For PDFs, renders the first page if PyMuPDF is available.
    - For images, resizes proportionally and converts to JPEG.
    Returns None if generation fails.
    """
    # PDF path
    if filename.lower().endswith(".pdf"):
        if fitz is not None:
            try:
                doc = fitz.open(stream=data, filetype="pdf")
                if doc.page_count < 1:
                    return None
                page = doc.load_page(0)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                # Reuse image pipeline below
                data = img_bytes
                # Fall through to image path
            except Exception:
                return None
        else:
            # If we cannot render PDFs, create a simple placeholder
            if Image is None:
                return None
            try:
                from PIL import ImageDraw, ImageFont  # type: ignore
            except Exception:
                ImageDraw = None  # type: ignore
                ImageFont = None  # type: ignore
            try:
                img = Image.new("RGB", (max_size, int(max_size * 1.3)), color=(245, 245, 245))
                draw = ImageDraw.Draw(img) if ImageDraw else None
                text = "PDF"
                if draw:
                    # Rough centering
                    w, h = draw.textsize(text) if hasattr(draw, "textsize") else (60, 20)
                    draw.text(((img.width - w) / 2, (img.height - h) / 2), text, fill=(120, 120, 120))
                out = BytesIO()
                img.save(out, format="JPEG", quality=80)
                return out.getvalue()
            except Exception:
                return None

    if Image is None:
        return None
    try:
        with Image.open(BytesIO(data)) as img:
            img = img.convert("RGB")
            w, h = img.size
            scale = min(1.0, float(max_size) / float(max(w, h)))
            if scale < 1.0:
                img = img.resize((int(w * scale), int(h * scale)))
            out = BytesIO()
            img.save(out, format="JPEG", quality=80)
            return out.getvalue()
    except Exception:
        return None
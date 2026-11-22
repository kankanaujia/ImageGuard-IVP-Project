"""Validate image signatures and decode image content without trusting extensions."""
from pathlib import Path
from PIL import Image

SUPPORTED_FORMATS = {"JPEG", "PNG", "TIFF", "BMP", "WEBP"}

def validate_image(path: Path) -> dict:
    try:
        with Image.open(path) as image:
            if image.format not in SUPPORTED_FORMATS:
                raise ValueError("Image signature is not supported")
            image.verify()
        # verify() checks the container, then reopen and force pixel decoding.
        with Image.open(path) as image:
            image.load()
            return {"format": image.format, "width": image.width, "height": image.height}
    except (OSError, SyntaxError) as exc:
        raise ValueError("File content is not a supported image") from exc

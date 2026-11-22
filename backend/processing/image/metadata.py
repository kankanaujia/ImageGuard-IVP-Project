"""Extract available image properties and EXIF tags."""
from pathlib import Path
from PIL import Image, ExifTags

def extract_metadata(source: Path) -> dict:
    with Image.open(source) as image:
        exif = image.getexif()
        tags = {ExifTags.TAGS.get(k, str(k)): str(v)[:500] for k, v in exif.items()}
        return {"format": image.format, "width": image.width, "height": image.height,
                "mode": image.mode, "exif": tags,
                "observations": ["No EXIF metadata available; this is common for edited, exported, or privacy-cleaned files."] if not tags else []}

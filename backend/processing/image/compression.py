"""JPEG compression history: estimated quality and the kind of quantization tables used.

The tables in a JPEG file record how it was last saved. Cameras usually write their own
custom tables; most software libraries (libjpeg/IJG, used by many editors, phones'
image libraries and web services) write the standard IJG tables scaled to a quality
setting. Matching IJG tables therefore suggest the file was last saved by software,
not necessarily straight from a camera. This is an observation, not proof of editing.
"""
from pathlib import Path
import numpy as np
from PIL import Image, JpegImagePlugin

IJG_LUMA = np.array([16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
                     14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
                     49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99], float)
SAMPLING = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}


def ijg_table(quality: int) -> np.ndarray:
    scale = 5000 / quality if quality < 50 else 200 - 2 * quality
    return np.clip(np.floor((IJG_LUMA * scale + 50) / 100), 1, 255)


def estimate_quality(luma: np.ndarray) -> tuple[float, bool]:
    """Closest IJG quality for a luminance table, and whether the table is (almost) exactly IJG."""
    errors = {q: float(np.abs(ijg_table(q) - luma).mean()) for q in range(1, 101)}
    best = min(errors, key=errors.get)
    return float(best), errors[best] < 0.5


def analyze_compression(source: Path) -> dict:
    with Image.open(source) as image:
        fmt = image.format
        if fmt != "JPEG":
            return {"format": fmt, "is_jpeg": False,
                    "observations": [f"{fmt} file: no JPEG quantization tables, so compression history cannot be read from the file itself."]}
        tables = getattr(image, "quantization", None) or {}
        progressive = bool(image.info.get("progressive") or image.info.get("progression"))
        try: sampling = SAMPLING.get(JpegImagePlugin.get_sampling(image), "other")
        except Exception: sampling = "unknown"
    if not tables:
        return {"format": fmt, "is_jpeg": True, "observations": ["No quantization tables could be read."]}
    luma = np.array(tables[0], float)
    quality, standard = estimate_quality(luma)
    observations = [f"Estimated JPEG quality ≈ {quality:.0f} (from the luminance quantization table)."]
    observations.append("Tables match the standard IJG tables: the file was most likely last saved by software rather than straight from a camera."
                        if standard else "Tables are not the standard IJG tables: typical of camera firmware or editors that use their own tables.")
    if quality >= 98:
        observations.append("Very high quality settings are unusual for cameras and common when images are re-exported.")
    return {"format": fmt, "is_jpeg": True, "estimated_quality": quality, "standard_ijg_tables": standard,
            "quantization_tables": len(tables), "chroma_subsampling": sampling, "progressive": progressive,
            "observations": observations,
            "note": "Compression settings describe how the file was last saved. Many legitimate workflows re-save images."}

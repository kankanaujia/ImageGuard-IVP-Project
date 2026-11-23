"""Block statistics and heat-map overlays shared by the localised image checks."""
from pathlib import Path
import cv2
import numpy as np

BLOCK = 16  # block size in pixels; two JPEG 8x8 blocks wide


def block_reduce(values: np.ndarray, block: int = BLOCK, reducer=np.mean) -> np.ndarray:
    """Reduce a 2-D array to one value per block (edge pixels that do not fill a block are dropped)."""
    h, w = values.shape[0] // block * block, values.shape[1] // block * block
    if h == 0 or w == 0:
        raise ValueError("Image is smaller than one analysis block")
    tiles = values[:h, :w].reshape(h // block, block, w // block, block).swapaxes(1, 2).reshape(h // block, w // block, -1)
    return reducer(tiles, axis=2)


def robust_z(blocks: np.ndarray) -> np.ndarray:
    """(x - median) / (1.4826 * MAD): how unusual each block is compared with the rest of the image."""
    median = float(np.median(blocks))
    mad = float(np.median(np.abs(blocks - median))) * 1.4826
    return (blocks - median) / max(mad, 1e-6)


def upsample(blocks: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Block grid -> full image size (smooth), for overlays and pixel-level evaluation."""
    return cv2.resize(blocks.astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_LINEAR)


def save_overlay(image_bgr: np.ndarray, heat: np.ndarray, out: Path, vmax: float) -> None:
    """Blend a heat map (0..vmax, block grid) over the image: transparent where low, red/yellow where high."""
    h, w = image_bgr.shape[:2]
    level = np.clip(upsample(heat, (h, w)) / vmax, 0, 1)
    colour = cv2.applyColorMap((level * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    grey = cv2.cvtColor(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    alpha = (0.15 + 0.7 * level)[..., None]           # low values let the photo show through
    blended = (grey * (1 - alpha) + colour * alpha).astype(np.uint8)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), blended):
        raise OSError(f"Could not save {out.name}")

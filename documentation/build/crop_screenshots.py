"""Crop the raw full-page screenshots (screenshots.ps1) into the report's figure images."""
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent / "screenshots"
CROPS = {  # output name: (raw page, (left, top, right, bottom)) in screenshot pixels
    "overview.png": ("overview", (0, 0, 1400, 500)),
    # investigation.png (batch queue in progress) is captured from the live browser, since it needs files queued
    "image_analysis.png": ("image", (0, 0, 1400, 930)),
    "image_slider.png": ("slider", (515, 500, 1370, 1215)),
    "image_cards.png": ("image", (530, 945, 1370, 1345)),
    "video_analysis.png": ("video", (0, 0, 1400, 920)),
    "video_frames.png": ("video", (540, 930, 1370, 1640)),
    "reports.png": ("reports", (0, 0, 1400, 1000)),
}
for name, (page, box) in CROPS.items():
    Image.open(HERE / "raw" / f"{page}.png").convert("RGB").crop(box).save(HERE / name)
    print(name, box)

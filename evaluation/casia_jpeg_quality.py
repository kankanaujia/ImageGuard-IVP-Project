"""Estimate the JPEG quality of CASIA v2.0 files per class, to explain the ELA results.

ELA's global peak depends on how a file was last compressed. If authentic and tampered
JPEGs were saved at systematically different qualities, ELA can separate the classes by
compression history rather than by the edit itself. Quality is estimated from each file's
luminance quantization table relative to the IJG standard table.

Usage (from the project root, after casia_eval has produced per_image.csv):
    backend\\.venv\\Scripts\\python.exe -m evaluation.casia_jpeg_quality <CASIA2 folder>
"""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from .casia_eval import OUT, find_split

IJG_LUMA = np.array([16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
                     18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99], float)


def estimate_quality(path: Path) -> float | None:
    with Image.open(path) as im:
        tables = getattr(im, "quantization", None)
    if not tables: return None
    scale = float(np.mean(np.array(tables[0], float) / IJG_LUMA) * 100)  # IJG scaling factor in percent
    return 100 - scale / 2 if scale <= 100 else 5000 / scale


def main() -> None:
    root = Path(sys.argv[1])
    folders = {0: find_split(root, "Au"), 1: find_split(root, "Tp")}
    rows = [r for r in csv.DictReader(open(OUT / "per_image.csv", encoding="utf-8")) if r["format"] == "jpg" and r["ela_peak"]]
    result = {}
    for label, name in ((0, "authentic"), (1, "tampered")):
        q, ela = [], []
        for r in (r for r in rows if int(r["label"]) == label):
            value = estimate_quality(folders[label] / r["file"])
            if value is not None: q.append(value); ela.append(float(r["ela_peak"]))
        q, ela = np.array(q), np.array(ela)
        values, counts = np.unique(np.round(q), return_counts=True)
        top = sorted(zip(counts.tolist(), values.tolist()), reverse=True)[:3]
        result[name] = {"n": int(len(q)), "quality_median": float(np.median(q)), "quality_p10": float(np.percentile(q, 10)),
                        "quality_p90": float(np.percentile(q, 90)), "most_common_quality": [{"quality": v, "share": c / len(q)} for c, v in top],
                        "ela_peak_median": float(np.median(ela))}
    (OUT / "jpeg_quality.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

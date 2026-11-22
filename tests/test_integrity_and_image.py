from pathlib import Path
from PIL import Image
from backend.utils.file_integrity import sha256_file, safe_extension
from backend.processing.image.ela import analyze_ela
from backend.processing.image.metadata import extract_metadata
from backend.processing.image.validation import validate_image

def test_sha256_and_suffix(tmp_path: Path):
    evidence = tmp_path / "evidence.bin"
    evidence.write_bytes(b"imageguard")
    assert sha256_file(evidence) == "3a60477ff20ab84ee6d15e4153dc7359b1f666ec1e08812d9d730f5c9d3f94c7"
    assert safe_extension("../../photo.JPG") == ".jpg"

def test_ela_and_metadata(tmp_path: Path):
    source = tmp_path / "test.png"
    Image.new("RGB", (24, 24), (120, 80, 30)).save(source)
    result = analyze_ela(source, tmp_path / "ela.png")
    assert (tmp_path / "ela.png").exists()
    assert result["quality"] == 90
    metadata = extract_metadata(source)
    assert metadata["width"] == 24
    assert metadata["height"] == 24
    assert validate_image(source)["format"] == "PNG"

def test_signature_validation_rejects_non_image(tmp_path: Path):
    source = tmp_path / "misleading.jpg"
    source.write_bytes(b"not an image")
    import pytest
    with pytest.raises(ValueError):
        validate_image(source)

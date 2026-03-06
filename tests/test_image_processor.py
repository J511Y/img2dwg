"""image_processor 모듈 테스트."""

import importlib
from pathlib import Path

import pytest
from PIL import Image

from img2dwg.data.image_processor import ImageProcessor


def test_image_processor_initialization():
    """ImageProcessor가 정상적으로 초기화되는지 테스트."""
    # Arrange & Act
    processor = ImageProcessor(target_size=(1024, 1024), quality=90)

    # Assert
    assert processor.target_size == (1024, 1024)
    assert processor.quality == 90


def test_to_base64_returns_data_url(tmp_path):
    """이미지가 base64 data URL로 변환되는지 테스트."""
    # Arrange
    processor = ImageProcessor()

    # 테스트용 이미지 생성
    test_image = tmp_path / "test.jpg"
    img = Image.new("RGB", (100, 100), color="red")
    img.save(test_image, "JPEG")

    # Act
    result = processor.to_base64(test_image)

    # Assert
    assert result.startswith("data:image/")
    assert "base64," in result
    assert len(result) > 100  # base64 인코딩된 데이터가 있어야 함


def test_resize_creates_output_file(tmp_path):
    """이미지 리사이징이 출력 파일을 생성하는지 테스트."""
    # Arrange
    processor = ImageProcessor()

    # 테스트용 이미지 생성 (큰 이미지)
    test_image = tmp_path / "large.jpg"
    img = Image.new("RGB", (3000, 2000), color="blue")
    img.save(test_image, "JPEG")

    output_path = tmp_path / "resized.jpg"

    # Act
    processor.resize(test_image, output_path, size=(800, 600))

    # Assert
    assert output_path.exists()

    # 리사이징된 이미지 확인
    resized_img = Image.open(output_path)
    assert resized_img.size[0] <= 800
    assert resized_img.size[1] <= 600


def test_process_nonexistent_file_raises_error():
    """존재하지 않는 이미지 처리 시 에러를 발생시키는지 테스트."""
    # Arrange
    processor = ImageProcessor()
    nonexistent_path = Path("nonexistent_image.jpg")

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        processor.process(nonexistent_path)


def test_process_converts_rgba_to_rgb(tmp_path):
    """RGBA 이미지가 RGB로 변환되는지 테스트."""
    # Arrange
    processor = ImageProcessor()

    # RGBA 이미지 생성
    test_image = tmp_path / "rgba.png"
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    img.save(test_image, "PNG")

    output_path = tmp_path / "processed.jpg"

    # Act
    result_path = processor.process(test_image, output_path)

    # Assert
    assert result_path.exists()
    processed_img = Image.open(result_path)
    assert processed_img.mode == "RGB"


def test_correct_distortion_raises_clear_error_when_opencv_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """opencv/numpy가 없는 환경에서도 명확한 오류 메시지를 반환한다."""
    processor = ImageProcessor()
    test_image = tmp_path / "test.jpg"
    Image.new("RGB", (64, 64), color="white").save(test_image, "JPEG")
    output_path = tmp_path / "distorted.jpg"

    original_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "cv2":
            raise ModuleNotFoundError("No module named 'cv2'")
        return original_import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(RuntimeError, match=r"선택 의존성\(opencv-python, numpy\)"):
        processor.correct_distortion(test_image, output_path)

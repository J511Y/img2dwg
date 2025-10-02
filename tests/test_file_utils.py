"""file_utils 모듈 테스트."""

from pathlib import Path
import tempfile
import pytest

from img2dwg.utils.file_utils import (
    ensure_dir,
    get_file_extension,
    is_image_file,
    is_dwg_file,
    is_dxf_file,
)


def test_ensure_dir_creates_directory():
    """ensure_dir이 디렉토리를 생성하는지 테스트."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test" / "nested" / "dir"
        
        # Act
        ensure_dir(test_dir)
        
        # Assert
        assert test_dir.exists()
        assert test_dir.is_dir()


def test_get_file_extension_returns_lowercase():
    """get_file_extension이 소문자 확장자를 반환하는지 테스트."""
    # Arrange & Act & Assert
    assert get_file_extension(Path("test.JPG")) == ".jpg"
    assert get_file_extension(Path("test.DWG")) == ".dwg"
    assert get_file_extension(Path("test.Txt")) == ".txt"


def test_is_image_file_identifies_images():
    """is_image_file이 이미지 파일을 정확히 식별하는지 테스트."""
    # Arrange & Act & Assert
    assert is_image_file(Path("test.jpg"))
    assert is_image_file(Path("test.PNG"))
    assert is_image_file(Path("test.jpeg"))
    assert not is_image_file(Path("test.dwg"))
    assert not is_image_file(Path("test.txt"))


def test_is_dwg_file_identifies_dwg():
    """is_dwg_file이 DWG 파일을 정확히 식별하는지 테스트."""
    # Arrange & Act & Assert
    assert is_dwg_file(Path("test.dwg"))
    assert is_dwg_file(Path("test.DWG"))
    assert not is_dwg_file(Path("test.dxf"))
    assert not is_dwg_file(Path("test.jpg"))


def test_is_dxf_file_identifies_dxf():
    """is_dxf_file이 DXF 파일을 정확히 식별하는지 테스트."""
    # Arrange & Act & Assert
    assert is_dxf_file(Path("test.dxf"))
    assert is_dxf_file(Path("test.DXF"))
    assert not is_dxf_file(Path("test.dwg"))
    assert not is_dxf_file(Path("test.jpg"))

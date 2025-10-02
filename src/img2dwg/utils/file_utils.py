"""파일 유틸리티 함수들."""

from pathlib import Path
from typing import List


def ensure_dir(path: Path) -> None:
    """
    디렉토리가 존재하지 않으면 생성한다.

    Args:
        path: 생성할 디렉토리 경로
    """
    path.mkdir(parents=True, exist_ok=True)


def get_file_extension(file_path: Path) -> str:
    """
    파일 확장자를 소문자로 반환한다.

    Args:
        file_path: 파일 경로

    Returns:
        확장자 (점 포함, 예: '.jpg')
    """
    return file_path.suffix.lower()


def is_image_file(file_path: Path) -> bool:
    """
    이미지 파일 여부를 확인한다.

    Args:
        file_path: 파일 경로

    Returns:
        이미지 파일이면 True
    """
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif"}
    return get_file_extension(file_path) in image_extensions


def is_dwg_file(file_path: Path) -> bool:
    """
    DWG 파일 여부를 확인한다.

    Args:
        file_path: 파일 경로

    Returns:
        DWG 파일이면 True
    """
    return get_file_extension(file_path) == ".dwg"


def is_dxf_file(file_path: Path) -> bool:
    """
    DXF 파일 여부를 확인한다.

    Args:
        file_path: 파일 경로

    Returns:
        DXF 파일이면 True
    """
    return get_file_extension(file_path) == ".dxf"


def get_files_by_extension(
    directory: Path,
    extensions: List[str],
    recursive: bool = False,
) -> List[Path]:
    """
    지정된 확장자를 가진 파일들을 찾는다.

    Args:
        directory: 검색할 디렉토리
        extensions: 확장자 리스트 (예: ['.jpg', '.png'])
        recursive: 하위 디렉토리까지 검색할지 여부

    Returns:
        찾은 파일 경로 리스트
    """
    files = []
    pattern = "**/*" if recursive else "*"

    for ext in extensions:
        ext_lower = ext.lower()
        files.extend(directory.glob(f"{pattern}{ext_lower}"))
        # 대소문자 구분 없이 검색
        files.extend(directory.glob(f"{pattern}{ext_lower.upper()}"))

    return sorted(set(files))

"""scanner 모듈 테스트."""

from pathlib import Path

import pytest

from img2dwg.data.scanner import DataScanner, FileGroup, ProjectData


def test_file_group_is_complete() -> None:
    """FileGroup의 is_complete 속성이 정상 작동하는지 테스트."""
    # Arrange
    group = FileGroup(type="변경")

    # Act & Assert - 빈 그룹
    assert not group.is_complete

    # 이미지만 추가
    group.images.append(Path("test.jpg"))
    assert not group.is_complete

    # DWG 추가
    group.dwg_files.append(Path("test.dwg"))
    assert group.is_complete


def test_project_data_has_change_files() -> None:
    """ProjectData의 has_change_files 속성 테스트."""
    # Arrange
    project = ProjectData(
        name="Test Project",
        path=Path("/test"),
        parent_folder="2501",
    )

    # Act & Assert - 초기 상태
    assert not project.has_change_files

    # 변경 파일 추가
    project.change_group.images.append(Path("test.jpg"))
    project.change_group.dwg_files.append(Path("test.dwg"))
    assert project.has_change_files


def test_project_data_is_incomplete() -> None:
    """ProjectData의 is_incomplete 속성 테스트."""
    # Arrange
    project = ProjectData(
        name="Test Project",
        path=Path("/test"),
        parent_folder="2501",
    )

    # Act & Assert - 초기 상태
    assert not project.is_incomplete

    # 이미지만 추가 (불완전)
    project.change_group.images.append(Path("test.jpg"))
    assert project.is_incomplete

    # DWG 추가 (완전)
    project.change_group.dwg_files.append(Path("test.dwg"))
    assert not project.is_incomplete


def test_data_scanner_raises_on_invalid_path() -> None:
    """DataScanner가 존재하지 않는 경로에 대해 에러를 발생시키는지 테스트."""
    # Arrange
    invalid_path = Path("/invalid/path/that/does/not/exist")

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        DataScanner(invalid_path)


def test_data_scanner_get_statistics(tmp_path: Path) -> None:
    """DataScanner의 get_statistics 메서드 테스트."""
    # Arrange
    scanner = DataScanner(tmp_path)

    # 테스트용 프로젝트 생성
    projects = [
        ProjectData(
            name="Complete Project",
            path=Path("/test1"),
            parent_folder="2501",
        ),
        ProjectData(
            name="Incomplete Project",
            path=Path("/test2"),
            parent_folder="2501",
        ),
    ]

    # 완전한 프로젝트
    projects[0].change_group.images.append(Path("test.jpg"))
    projects[0].change_group.dwg_files.append(Path("test.dwg"))

    # 불완전한 프로젝트 (이미지만)
    projects[1].change_group.images.append(Path("test.jpg"))

    # Act
    stats = scanner.get_statistics(projects)

    # Assert
    assert stats["total_projects"] == 2
    assert stats["complete_change_pairs"] == 1
    assert stats["incomplete_projects"] == 1
    assert len(stats["incomplete_details"]) == 1

"""데이터 폴더 스캔 및 분류 모듈."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from ..utils.logger import get_logger
from ..utils.file_utils import is_image_file, is_dwg_file


logger = get_logger(__name__)


@dataclass
class FileGroup:
    """
    파일 그룹 (변경 또는 단면도).
    
    Attributes:
        type: 파일 타입 ('변경' 또는 '단면')
        images: 이미지 파일 목록
        dwg_files: DWG 파일 목록
    """
    type: str  # '변경' 또는 '단면'
    images: List[Path] = field(default_factory=list)
    dwg_files: List[Path] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """이미지와 DWG 파일이 모두 있는지 확인."""
        return len(self.images) > 0 and len(self.dwg_files) > 0

    @property
    def image_count(self) -> int:
        """이미지 개수."""
        return len(self.images)

    @property
    def dwg_count(self) -> int:
        """DWG 파일 개수."""
        return len(self.dwg_files)


@dataclass
class ProjectData:
    """
    프로젝트 데이터.
    
    Attributes:
        name: 프로젝트 이름
        path: 프로젝트 경로
        parent_folder: 상위 폴더명
        change_group: 변경 관련 파일 그룹
        section_group: 단면도 관련 파일 그룹
    """
    name: str
    path: Path
    parent_folder: str
    change_group: FileGroup = field(default_factory=lambda: FileGroup(type="변경"))
    section_group: FileGroup = field(default_factory=lambda: FileGroup(type="단면"))

    @property
    def has_change_files(self) -> bool:
        """변경 관련 파일이 있는지 확인."""
        return self.change_group.is_complete

    @property
    def has_section_files(self) -> bool:
        """단면도 관련 파일이 있는지 확인."""
        return self.section_group.is_complete

    @property
    def is_incomplete(self) -> bool:
        """불완전한 데이터인지 확인 (이미지만 있거나 DWG만 있는 경우)."""
        change_incomplete = (
            len(self.change_group.images) > 0 or len(self.change_group.dwg_files) > 0
        ) and not self.change_group.is_complete
        
        section_incomplete = (
            len(self.section_group.images) > 0 or len(self.section_group.dwg_files) > 0
        ) and not self.section_group.is_complete
        
        return change_incomplete or section_incomplete


class DataScanner:
    """데이터 폴더를 스캔하고 파일을 분류하는 클래스."""

    def __init__(self, data_path: Path):
        """
        DataScanner를 초기화한다.

        Args:
            data_path: 데이터 폴더 경로 (예: datas/)
        
        Raises:
            FileNotFoundError: 데이터 경로가 존재하지 않을 때
        """
        if not data_path.exists():
            raise FileNotFoundError(f"데이터 경로를 찾을 수 없습니다: {data_path}")
        
        self.data_path = data_path
        logger.info(f"DataScanner 초기화: {data_path}")

    def scan(self) -> List[ProjectData]:
        """
        데이터 폴더를 스캔하여 프로젝트 목록을 반환한다.

        Returns:
            프로젝트 데이터 리스트
        """
        logger.info("데이터 스캔 시작")
        projects = []

        # 상위 폴더 순회 (예: 2501 (2), 2501 (3) 등)
        for parent_folder in self.data_path.iterdir():
            if not parent_folder.is_dir():
                continue

            logger.debug(f"상위 폴더 스캔: {parent_folder.name}")

            # 프로젝트 폴더 순회
            for project_folder in parent_folder.iterdir():
                if not project_folder.is_dir():
                    continue

                project = self._scan_project(project_folder, parent_folder.name)
                if project:
                    projects.append(project)

        logger.info(f"스캔 완료: 총 {len(projects)}개 프로젝트 발견")
        return projects

    def _scan_project(self, project_path: Path, parent_folder: str) -> Optional[ProjectData]:
        """
        개별 프로젝트 폴더를 스캔한다.

        Args:
            project_path: 프로젝트 폴더 경로
            parent_folder: 상위 폴더명

        Returns:
            ProjectData 객체 또는 None
        """
        logger.debug(f"프로젝트 스캔: {project_path.name}")

        project = ProjectData(
            name=project_path.name,
            path=project_path,
            parent_folder=parent_folder,
        )

        # 프로젝트 폴더 내 모든 파일 검사
        for file_path in project_path.iterdir():
            if not file_path.is_file():
                continue

            self._classify_file(file_path, project)

        return project

    def _classify_file(self, file_path: Path, project: ProjectData) -> None:
        """
        파일을 분류하여 프로젝트 데이터에 추가한다.

        Args:
            file_path: 파일 경로
            project: 프로젝트 데이터
        """
        filename = file_path.name.lower()

        # 변경 관련 파일
        if "변경" in filename:
            if is_image_file(file_path):
                project.change_group.images.append(file_path)
                logger.debug(f"변경 이미지 발견: {file_path.name}")
            elif is_dwg_file(file_path):
                project.change_group.dwg_files.append(file_path)
                logger.debug(f"변경 DWG 발견: {file_path.name}")

        # 단면도 관련 파일
        if "단면" in filename:
            if is_image_file(file_path):
                project.section_group.images.append(file_path)
                logger.debug(f"단면 이미지 발견: {file_path.name}")
            elif is_dwg_file(file_path):
                project.section_group.dwg_files.append(file_path)
                logger.debug(f"단면 DWG 발견: {file_path.name}")

    def get_statistics(self, projects: List[ProjectData]) -> dict:
        """
        프로젝트 통계를 계산한다.

        Args:
            projects: 프로젝트 데이터 리스트

        Returns:
            통계 딕셔너리
        """
        complete_change = sum(1 for p in projects if p.has_change_files)
        complete_section = sum(1 for p in projects if p.has_section_files)
        incomplete = [p for p in projects if p.is_incomplete]

        stats = {
            "total_projects": len(projects),
            "complete_change_pairs": complete_change,
            "complete_section_pairs": complete_section,
            "incomplete_projects": len(incomplete),
            "incomplete_details": [
                {
                    "name": p.name,
                    "parent_folder": p.parent_folder,
                    "change_images": p.change_group.image_count,
                    "change_dwgs": p.change_group.dwg_count,
                    "section_images": p.section_group.image_count,
                    "section_dwgs": p.section_group.dwg_count,
                }
                for p in incomplete
            ],
        }

        return stats

"""이미지를 공개 URL로 업로드하는 유틸리티."""

import base64
import json
import os
from pathlib import Path
from typing import Optional

import requests

from .logger import get_logger

logger = get_logger(__name__)


class ImageUploader:
    """이미지를 공개 서비스에 업로드하는 클래스."""

    def __init__(self, service: str = "github", api_key: Optional[str] = None):
        """
        ImageUploader 초기화.

        Args:
            service: 업로드 서비스 (imgur, cloudinary, github)
            api_key: API 키 (환경변수에서 자동 로드)
        """
        self.service = service.lower()
        self.api_key = api_key or self._get_api_key()

    def _get_api_key(self) -> Optional[str]:
        """환경변수에서 API 키를 가져온다."""
        if self.service == "imgur":
            return os.getenv("IMGUR_CLIENT_ID")
        elif self.service == "cloudinary":
            return os.getenv("CLOUDINARY_URL")
        elif self.service == "github":
            return os.getenv("GITHUB_TOKEN")
        return None

    def upload(self, image_path: Path, project_name: Optional[str] = None) -> str:
        """
        이미지를 업로드하고 공개 URL을 반환한다.

        Args:
            image_path: 업로드할 이미지 경로
            project_name: 프로젝트명 (폴더 구조에 사용)

        Returns:
            공개 이미지 URL

        Raises:
            ValueError: 지원하지 않는 서비스
            RuntimeError: 업로드 실패
        """
        if self.service == "imgur":
            return self._upload_imgur(image_path)
        elif self.service == "cloudinary":
            return self._upload_cloudinary(image_path, project_name)
        elif self.service == "github":
            return self._upload_github(image_path, project_name)
        else:
            raise ValueError(f"지원하지 않는 서비스: {self.service}")

    def _upload_imgur(self, image_path: Path) -> str:
        """
        Imgur에 이미지를 업로드한다.

        Args:
            image_path: 이미지 경로

        Returns:
            Imgur URL
        """
        if not self.api_key:
            raise RuntimeError(
                "Imgur Client ID가 필요합니다. "
                "환경변수 IMGUR_CLIENT_ID를 설정하세요.\n"
                "https://api.imgur.com/oauth2/addclient 에서 발급받을 수 있습니다."
            )

        logger.info(f"Imgur에 업로드 중: {image_path.name}")

        # 이미지를 base64로 인코딩
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Imgur API 호출
        headers = {"Authorization": f"Client-ID {self.api_key}"}
        data = {"image": image_data, "type": "base64"}

        response = requests.post(
            "https://api.imgur.com/3/image",
            headers=headers,
            data=data,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Imgur 업로드 실패: {response.status_code}\n{response.text}"
            )

        result = response.json()
        url = result["data"]["link"]

        logger.info(f"✅ 업로드 완료: {url}")
        return url

    def _upload_cloudinary(self, image_path: Path, project_name: Optional[str] = None) -> str:
        """
        Cloudinary에 이미지를 업로드한다.

        Args:
            image_path: 이미지 경로
            project_name: 프로젝트명 (폴더 구조에 사용)

        Returns:
            Cloudinary URL
        """
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError:
            raise RuntimeError(
                "cloudinary 패키지가 필요합니다: uv add cloudinary"
            )

        if not self.api_key:
            raise RuntimeError(
                "Cloudinary URL이 필요합니다. "
                "환경변수 CLOUDINARY_URL을 설정하세요.\n"
                "형식: cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
            )

        logger.info(f"Cloudinary에 업로드 중: {image_path.name}")

        # Cloudinary 설정
        cloudinary.config(cloudinary_url=self.api_key)

        # 폴더 경로 생성
        folder = "img2dwg"
        if project_name:
            # 프로젝트명을 폴더에 포함 (특수문자 제거)
            safe_project = project_name.replace(" ", "_").replace("/", "_")
            folder = f"img2dwg/{safe_project}"

        # 업로드
        result = cloudinary.uploader.upload(
            str(image_path),
            folder=folder,
            resource_type="image",
        )

        url = result["secure_url"]
        logger.info(f"✅ 업로드 완료: {url}")
        return url

    def _upload_github(self, image_path: Path, project_name: Optional[str] = None) -> str:
        """
        GitHub에 이미지를 업로드한다.

        Args:
            image_path: 이미지 경로
            project_name: 프로젝트명 (폴더 구조에 사용)

        Returns:
            GitHub raw URL
        """
        if not self.api_key:
            raise RuntimeError(
                "GitHub Token이 필요합니다. "
                "환경변수 GITHUB_TOKEN을 설정하세요.\n"
                "https://github.com/settings/tokens 에서 발급받을 수 있습니다."
            )

        # GitHub 저장소 정보 (환경변수에서 읽기)
        repo_owner = os.getenv("GITHUB_REPO_OWNER", "your-username")
        repo_name = os.getenv("GITHUB_REPO_NAME", "img2dwg-images")
        branch = os.getenv("GITHUB_BRANCH", "main")

        # 파일 경로 생성 (프로젝트명 포함)
        if project_name:
            # 프로젝트명을 URL-safe하게 변환
            import urllib.parse
            safe_project = urllib.parse.quote(project_name)
            file_path = f"images/{safe_project}/{image_path.name}"
        else:
            file_path = f"images/{image_path.name}"

        logger.info(f"GitHub에 업로드 중: {file_path}")

        # 이미지를 base64로 인코딩
        with open(image_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        # GitHub API 호출
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"

        headers = {
            "Authorization": f"token {self.api_key}",
            "Accept": "application/vnd.github.v3+json",
        }

        # 기존 파일이 있는지 확인 (SHA 가져오기)
        get_response = requests.get(url, headers=headers, timeout=10)
        
        data = {
            "message": f"Upload {project_name}/{image_path.name}" if project_name else f"Upload {image_path.name}",
            "content": content,
            "branch": branch,
        }
        
        # 기존 파일이 있으면 SHA 추가 (업데이트)
        if get_response.status_code == 200:
            existing_sha = get_response.json()["sha"]
            data["sha"] = existing_sha
            logger.debug(f"기존 파일 업데이트: {file_path}")

        response = requests.put(url, headers=headers, json=data, timeout=30)

        if response.status_code not in [200, 201]:
            raise RuntimeError(
                f"GitHub 업로드 실패: {response.status_code}\n{response.text}"
            )

        # Raw URL 생성
        raw_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/{file_path}"

        logger.info(f"✅ 업로드 완료: {raw_url}")
        return raw_url


class URLCache:
    """업로드된 이미지 URL 캐시."""

    def __init__(self, cache_file: Path):
        """
        URLCache 초기화.

        Args:
            cache_file: 캐시 파일 경로
        """
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """캐시 파일을 로드한다."""
        if self.cache_file.exists():
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self) -> None:
        """캐시를 파일에 저장한다."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get(self, image_path: Path) -> Optional[str]:
        """
        캐시에서 URL을 가져온다.

        Args:
            image_path: 이미지 경로

        Returns:
            캐시된 URL (없으면 None)
        """
        key = str(image_path.resolve())
        return self.cache.get(key)

    def set(self, image_path: Path, url: str) -> None:
        """
        URL을 캐시에 저장한다.

        Args:
            image_path: 이미지 경로
            url: 업로드된 URL
        """
        key = str(image_path.resolve())
        self.cache[key] = url
        self._save_cache()
        logger.debug(f"캐시 저장: {image_path.name} → {url}")

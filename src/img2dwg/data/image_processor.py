"""이미지 전처리 모듈."""

from pathlib import Path
from typing import Tuple, Optional
import base64

from ..utils.logger import get_logger


logger = get_logger(__name__)


class ImageProcessor:
    """이미지 전처리를 수행하는 클래스."""

    def __init__(
        self,
        target_size: Tuple[int, int] = (2048, 2048),
        quality: int = 85,
    ):
        """
        ImageProcessor를 초기화한다.

        Args:
            target_size: 목표 이미지 크기 (width, height)
            quality: JPEG 품질 (1-100)
        """
        self.target_size = target_size
        self.quality = quality
        logger.info(f"ImageProcessor 초기화: size={target_size}, quality={quality}")

    def process(
        self,
        image_path: Path,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        이미지를 전처리한다.

        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 이미지 경로 (None이면 임시 경로 생성)

        Returns:
            처리된 이미지 경로

        Raises:
            FileNotFoundError: 이미지 파일이 존재하지 않을 때

        Note:
            실제 구현 시 Pillow, OpenCV 사용
            현재는 스텁(stub) 구현
        """
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        logger.info(f"이미지 전처리 시작: {image_path}")

        # TODO: Pillow/OpenCV를 사용한 실제 전처리 구현
        # from PIL import Image
        # import cv2
        # 
        # 1. 이미지 로드
        # 2. 해상도 정규화
        # 3. 노이즈 제거
        # 4. 왜곡 보정 (필요시)
        # 5. 명암 정규화
        # 6. 저장

        logger.warning(
            "이미지 전처리는 현재 스텁 구현입니다. "
            "Pillow/OpenCV를 설치하고 구현하세요."
        )

        # 스텁: 원본 경로 반환
        return image_path

    def to_base64(self, image_path: Path) -> str:
        """
        이미지를 base64 인코딩한다.

        Args:
            image_path: 이미지 파일 경로

        Returns:
            base64 인코딩된 문자열 (data URL 형식)
        """
        with open(image_path, "rb") as f:
            image_data = f.read()

        encoded = base64.b64encode(image_data).decode("utf-8")
        ext = image_path.suffix.lower().lstrip(".")
        
        # MIME type 결정
        mime_type = f"image/{ext if ext in ['png', 'jpeg', 'jpg'] else 'jpeg'}"
        
        return f"data:{mime_type};base64,{encoded}"

    def resize(
        self,
        image_path: Path,
        output_path: Path,
        size: Optional[Tuple[int, int]] = None,
    ) -> None:
        """
        이미지 크기를 조절한다.

        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 이미지 경로
            size: 목표 크기 (None이면 self.target_size 사용)

        Note:
            실제 구현 시 Pillow 사용
        """
        target = size or self.target_size
        
        # TODO: Pillow를 사용한 실제 리사이징 구현
        # from PIL import Image
        # img = Image.open(image_path)
        # img_resized = img.resize(target, Image.LANCZOS)
        # img_resized.save(output_path, quality=self.quality)
        
        logger.warning("이미지 리사이징은 현재 스텁 구현입니다.")

    def correct_distortion(self, image_path: Path, output_path: Path) -> None:
        """
        이미지 왜곡을 보정한다.

        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 이미지 경로

        Note:
            실제 구현 시 OpenCV의 perspective transform 사용
        """
        # TODO: OpenCV를 사용한 왜곡 보정 구현
        # import cv2
        # import numpy as np
        # 
        # 1. 이미지 로드
        # 2. 코너 검출
        # 3. Perspective transform 적용
        # 4. 저장
        
        logger.warning("왜곡 보정은 현재 스텁 구현입니다.")

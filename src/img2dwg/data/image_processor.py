"""이미지 전처리 모듈."""

from pathlib import Path
from typing import Tuple, Optional
import base64

import cv2
import numpy as np
from PIL import Image

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
            output_path: 출력 이미지 경로 (None이면 원본 경로로 덮어쓰기)

        Returns:
            처리된 이미지 경로

        Raises:
            FileNotFoundError: 이미지 파일이 존재하지 않을 때
        """
        if not image_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

        logger.info(f"이미지 전처리 시작: {image_path}")

        try:
            # Pillow로 이미지 로드
            img = Image.open(image_path)
            
            # RGBA -> RGB 변환 (투명도 제거)
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
            
            # 이미지 크기가 목표보다 크면 리사이징 (비율 유지)
            original_size = img.size
            if img.size[0] > self.target_size[0] or img.size[1] > self.target_size[1]:
                img.thumbnail(self.target_size, Image.Resampling.LANCZOS)
                logger.info(f"이미지 리사이징: {original_size} -> {img.size}")
            
            # 출력 경로 설정
            if output_path is None:
                output_path = image_path
            
            # 저장
            img.save(output_path, "JPEG", quality=self.quality, optimize=True)
            logger.info(f"이미지 전처리 완료: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"이미지 전처리 실패: {e}")
            raise RuntimeError(f"이미지 전처리 중 오류 발생: {e}") from e

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
        """
        target = size or self.target_size
        
        try:
            # Pillow로 이미지 로드 및 리사이징
            img = Image.open(image_path)
            
            # 비율 유지하면서 리사이징
            img.thumbnail(target, Image.Resampling.LANCZOS)
            
            # 저장
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "JPEG", quality=self.quality, optimize=True)
            
            logger.info(f"이미지 리사이징 완료: {image_path.name} -> {output_path}")
            
        except Exception as e:
            logger.error(f"이미지 리사이징 실패: {e}")
            raise RuntimeError(f"이미지 리사이징 중 오류 발생: {e}") from e

    def correct_distortion(self, image_path: Path, output_path: Path) -> None:
        """
        이미지 왜곡을 보정한다 (간단한 노이즈 제거 및 대비 개선).

        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 이미지 경로

        Note:
            자동 코너 검출은 복잡하므로, 여기서는 노이즈 제거와 대비 개선만 수행합니다.
            필요 시 수동으로 코너를 지정하는 메서드를 추가할 수 있습니다.
        """
        try:
            # OpenCV로 이미지 로드
            img = cv2.imread(str(image_path))
            
            if img is None:
                raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")
            
            # 1. 노이즈 제거 (bilateral filter)
            denoised = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
            
            # 2. 대비 개선 (CLAHE - Contrast Limited Adaptive Histogram Equalization)
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            
            enhanced = cv2.merge((cl, a, b))
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # 3. 샤프닝 (선택적)
            kernel = np.array([[-1, -1, -1],
                               [-1,  9, -1],
                               [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # 저장
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), sharpened, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            
            logger.info(f"이미지 왜곡 보정 완료: {output_path}")
            
        except Exception as e:
            logger.error(f"이미지 왜곡 보정 실패: {e}")
            raise RuntimeError(f"이미지 왜곡 보정 중 오류 발생: {e}") from e

"""이미지 전처리 모듈."""

from __future__ import annotations

import base64
import importlib
from pathlib import Path
from typing import Any

from PIL import Image

from ..utils.logger import get_logger

logger = get_logger(__name__)


def calculate_image_bbox(image_path: Path) -> tuple[float, float, float, float]:
    """
    이미지의 바운딩박스를 계산한다 (픽셀 좌표).

    Args:
        image_path: 이미지 파일 경로

    Returns:
        (xmin, ymin, xmax, ymax) 튜플
    """
    with Image.open(image_path) as img:
        width, height = img.size
        return (0, 0, width, height)


class ImageProcessor:
    """이미지 전처리를 수행하는 클래스."""

    def __init__(
        self,
        target_size: tuple[int, int] = (2048, 2048),
        quality: int = 85,
    ) -> None:
        """
        ImageProcessor를 초기화한다.

        Args:
            target_size: 목표 이미지 크기 (width, height)
            quality: JPEG 품질 (1-100)
        """
        self.target_size = target_size
        self.quality = quality
        logger.info("ImageProcessor 초기화: size=%s, quality=%s", target_size, quality)

    def process(
        self,
        image_path: Path,
        output_path: Path | None = None,
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

        logger.info("이미지 전처리 시작: %s", image_path)

        try:
            img: Image.Image = Image.open(image_path)

            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            original_size = img.size
            if img.size[0] > self.target_size[0] or img.size[1] > self.target_size[1]:
                img.thumbnail(self.target_size, Image.Resampling.LANCZOS)
                logger.info("이미지 리사이징: %s -> %s", original_size, img.size)

            output_path = output_path or image_path
            img.save(output_path, "JPEG", quality=self.quality, optimize=True)
            logger.info("이미지 전처리 완료: %s", output_path)
            return output_path

        except Exception as exc:
            logger.error("이미지 전처리 실패: %s", exc)
            raise RuntimeError(f"이미지 전처리 중 오류 발생: {exc}") from exc

    def to_base64(self, image_path: Path) -> str:
        """
        이미지를 base64 인코딩한다.

        Args:
            image_path: 이미지 파일 경로

        Returns:
            base64 인코딩된 문자열 (data URL 형식)
        """
        with image_path.open("rb") as file:
            image_data = file.read()

        encoded = base64.b64encode(image_data).decode("utf-8")
        ext = image_path.suffix.lower().lstrip(".")
        mime_type = f"image/{ext if ext in ['png', 'jpeg', 'jpg'] else 'jpeg'}"
        return f"data:{mime_type};base64,{encoded}"

    def resize(
        self,
        image_path: Path,
        output_path: Path,
        size: tuple[int, int] | None = None,
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
            img: Image.Image = Image.open(image_path)
            img.thumbnail(target, Image.Resampling.LANCZOS)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "JPEG", quality=self.quality, optimize=True)
            logger.info("이미지 리사이징 완료: %s -> %s", image_path.name, output_path)

        except Exception as exc:
            logger.error("이미지 리사이징 실패: %s", exc)
            raise RuntimeError(f"이미지 리사이징 중 오류 발생: {exc}") from exc

    @staticmethod
    def _load_opencv_dependencies() -> tuple[Any, Any]:
        """Load optional OpenCV stack lazily to reduce env-dependent import failures."""
        try:
            cv2 = importlib.import_module("cv2")
            np = importlib.import_module("numpy")
            return cv2, np
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "이미지 왜곡 보정에는 선택 의존성(opencv-python, numpy)이 필요합니다. "
                "`uv sync` 또는 `uv pip install opencv-python numpy` 후 다시 시도하세요."
            ) from exc

    def correct_distortion(self, image_path: Path, output_path: Path) -> None:
        """
        이미지 왜곡을 보정한다 (간단한 노이즈 제거 및 대비 개선).

        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 이미지 경로
        """
        try:
            cv2, np = self._load_opencv_dependencies()
            img = cv2.imread(str(image_path))

            if img is None:
                raise ValueError(f"이미지를 로드할 수 없습니다: {image_path}")

            denoised = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            lightness, a_channel, b_channel = cv2.split(lab)

            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            cl = clahe.apply(lightness)

            enhanced = cv2.merge((cl, a_channel, b_channel))
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(output_path), sharpened, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            logger.info("이미지 왜곡 보정 완료: %s", output_path)

        except Exception as exc:
            logger.error("이미지 왜곡 보정 실패: %s", exc)
            raise RuntimeError(f"이미지 왜곡 보정 중 오류 발생: {exc}") from exc

    def crop(
        self,
        image_path: Path,
        output_path: Path,
        bbox: tuple[int, int, int, int],
    ) -> None:
        """
        이미지를 지정된 영역으로 크롭한다.

        Args:
            image_path: 입력 이미지 경로
            output_path: 출력 이미지 경로
            bbox: 크롭 영역 (left, top, right, bottom) 픽셀 좌표
        """
        try:
            with Image.open(image_path) as img:
                cropped = img.crop(bbox)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                cropped.save(output_path, "JPEG", quality=self.quality, optimize=True)
                logger.info("이미지 크롭 완료: %s", output_path)

        except Exception as exc:
            logger.error("이미지 크롭 실패: %s", exc)
            raise RuntimeError(f"이미지 크롭 중 오류 발생: {exc}") from exc

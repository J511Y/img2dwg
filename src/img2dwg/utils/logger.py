"""로깅 설정 모듈."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    log_format: Optional[str] = None,
) -> None:
    """
    로깅을 설정한다.

    Args:
        log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 콘솔에만 출력)
        log_format: 로그 포맷 문자열
    """
    if log_format is None:
        log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # 파일 핸들러 (지정된 경우)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    지정된 이름의 로거를 반환한다.

    Args:
        name: 로거 이름 (보통 __name__ 사용)

    Returns:
        Logger 인스턴스
    """
    return logging.getLogger(name)

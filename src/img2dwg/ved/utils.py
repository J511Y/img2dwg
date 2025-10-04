"""Vision Encoder-Decoder 유틸리티 함수."""

import json
import random
from typing import Any, Dict

import numpy as np
import torch


def set_seed(seed: int):
    """
    재현성을 위한 random seed 설정.
    
    Args:
        seed: Random seed
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # CuDNN 결정론적 모드
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def validate_json(json_str: str) -> bool:
    """
    JSON 문자열이 유효한지 검증한다.
    
    Args:
        json_str: JSON 문자열
    
    Returns:
        유효하면 True, 아니면 False
    """
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False


def parse_json_safe(json_str: str) -> Dict[str, Any]:
    """
    JSON 문자열을 안전하게 파싱한다.
    
    Args:
        json_str: JSON 문자열
    
    Returns:
        파싱된 딕셔너리 (실패 시 빈 딕셔너리)
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return {}


def count_parameters(model: torch.nn.Module) -> int:
    """
    모델의 학습 가능한 파라미터 수를 계산한다.
    
    Args:
        model: PyTorch 모델
    
    Returns:
        파라미터 수
    """
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def format_time(seconds: float) -> str:
    """
    초를 읽기 쉬운 형식으로 변환한다.
    
    Args:
        seconds: 초
    
    Returns:
        포맷된 시간 문자열 (예: "1h 23m 45s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def get_device() -> str:
    """
    사용 가능한 디바이스를 반환한다.
    
    Returns:
        "cuda" 또는 "cpu"
    """
    return "cuda" if torch.cuda.is_available() else "cpu"


def print_gpu_memory():
    """GPU 메모리 사용량을 출력한다."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        print(f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")

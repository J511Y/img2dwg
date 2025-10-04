"""Vision Encoder-Decoder 학습용 데이터셋."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from .tokenizer import CADTokenizer


class ImageToJSONDataset(Dataset):
    """
    이미지→JSON 변환을 위한 데이터셋.
    
    JSONL 파일에서 이미지 URL과 JSON 데이터를 로드하여
    Vision Encoder-Decoder 학습에 사용할 수 있는 형태로 변환한다.
    """
    
    def __init__(
        self,
        jsonl_path: Path,
        tokenizer: CADTokenizer,
        image_size: int = 384,
        max_length: int = 2048,
        image_dir: Optional[Path] = None,
    ):
        """
        ImageToJSONDataset을 초기화한다.
        
        Args:
            jsonl_path: JSONL 파일 경로
            tokenizer: CAD 토크나이저
            image_size: 이미지 리사이즈 크기
            max_length: 최대 토큰 길이
            image_dir: 이미지 디렉토리 (URL이 아닌 로컬 경로인 경우)
        """
        self.jsonl_path = jsonl_path
        self.tokenizer = tokenizer
        self.image_size = image_size
        self.max_length = max_length
        self.image_dir = image_dir
        
        # 데이터 로드
        self.samples = self._load_samples()
        
        # 이미지 전처리 변환
        self.transform = transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],  # ImageNet 평균
                std=[0.229, 0.224, 0.225],   # ImageNet 표준편차
            ),
        ])
    
    def _load_samples(self) -> List[Dict[str, Any]]:
        """
        JSONL 파일에서 샘플을 로드한다.
        
        Returns:
            샘플 리스트
        """
        samples = []
        
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line)
                
                # OpenAI 파인튜닝 형식에서 추출
                messages = record.get("messages", [])
                
                # User 메시지에서 이미지 URL 추출
                user_msg = next((m for m in messages if m["role"] == "user"), None)
                if not user_msg:
                    continue
                
                # Assistant 메시지에서 JSON 추출
                assistant_msg = next((m for m in messages if m["role"] == "assistant"), None)
                if not assistant_msg:
                    continue
                
                # 이미지 URL 추출 (첫 번째 이미지만 사용)
                content = user_msg.get("content", [])
                image_url = None
                for item in content:
                    if item.get("type") == "image_url":
                        image_url = item["image_url"]["url"]
                        break
                
                if not image_url:
                    continue
                
                # JSON 데이터
                json_str = assistant_msg["content"]
                
                samples.append({
                    "image_url": image_url,
                    "json_str": json_str,
                })
        
        return samples
    
    def _load_image(self, image_url: str) -> Image.Image:
        """
        이미지를 로드한다.
        
        Args:
            image_url: 이미지 URL 또는 경로
        
        Returns:
            PIL Image
        """
        # URL인 경우 (base64 또는 http)
        if image_url.startswith("data:image"):
            # Base64 디코딩
            import base64
            import io
            
            header, encoded = image_url.split(",", 1)
            image_data = base64.b64decode(encoded)
            return Image.open(io.BytesIO(image_data)).convert("RGB")
        
        elif image_url.startswith("http"):
            # HTTP URL에서 다운로드
            import requests
            from io import BytesIO
            
            response = requests.get(image_url)
            return Image.open(BytesIO(response.content)).convert("RGB")
        
        else:
            # 로컬 파일 경로
            if self.image_dir:
                image_path = self.image_dir / image_url
            else:
                image_path = Path(image_url)
            
            return Image.open(image_path).convert("RGB")
    
    def __len__(self) -> int:
        """데이터셋 크기를 반환한다."""
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        샘플을 반환한다.
        
        Args:
            idx: 샘플 인덱스
        
        Returns:
            {
                "pixel_values": 이미지 텐서 (C, H, W),
                "labels": 타겟 토큰 ID (max_length,)
            }
        """
        sample = self.samples[idx]
        
        # 이미지 로드 및 전처리
        try:
            image = self._load_image(sample["image_url"])
            pixel_values = self.transform(image)
        except Exception as e:
            print(f"Error loading image {sample['image_url']}: {e}")
            # 에러 시 검은색 이미지 반환
            pixel_values = torch.zeros(3, self.image_size, self.image_size)
        
        # JSON 토큰화
        json_str = sample["json_str"]
        encoding = self.tokenizer(
            json_str,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        
        labels = encoding["input_ids"].squeeze(0)
        
        return {
            "pixel_values": pixel_values,
            "labels": labels,
        }


def collate_fn(batch: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
    """
    배치 collate 함수.
    
    Args:
        batch: 샘플 리스트
    
    Returns:
        배치 딕셔너리
    """
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    labels = torch.stack([item["labels"] for item in batch])
    
    return {
        "pixel_values": pixel_values,
        "labels": labels,
    }

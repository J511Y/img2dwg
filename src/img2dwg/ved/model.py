"""Vision Encoder-Decoder 모델 정의."""

from pathlib import Path
from typing import Optional

import torch
from transformers import (
    AutoImageProcessor,
    VisionEncoderDecoderModel,
)

from .config import VEDConfig
from .tokenizer import CADTokenizer


class VEDModel:
    """
    Vision Encoder-Decoder 모델 래퍼.
    
    HuggingFace의 VisionEncoderDecoderModel을 래핑하여
    이미지→JSON 변환에 특화된 인터페이스를 제공한다.
    """
    
    def __init__(
        self,
        config: VEDConfig,
        tokenizer: CADTokenizer,
    ):
        """
        VEDModel을 초기화한다.
        
        Args:
            config: 모델 설정
            tokenizer: CAD 토크나이저
        """
        self.config = config
        self.tokenizer = tokenizer
        
        # 이미지 프로세서 (encoder용)
        self.image_processor = AutoImageProcessor.from_pretrained(config.encoder_model)
        
        # 모델 초기화
        self.model = self._build_model()
    
    def _build_model(self) -> VisionEncoderDecoderModel:
        """
        Vision Encoder-Decoder 모델을 구축한다.
        
        Returns:
            VisionEncoderDecoderModel
        """
        print(f"Building VED model:")
        print(f"  Encoder: {self.config.encoder_model}")
        print(f"  Decoder: {self.config.decoder_model}")
        
        # Pre-trained encoder + decoder 결합
        model = VisionEncoderDecoderModel.from_encoder_decoder_pretrained(
            self.config.encoder_model,
            self.config.decoder_model,
        )
        
        # Decoder 설정
        model.config.decoder_start_token_id = self.tokenizer.bos_token_id
        model.config.pad_token_id = self.tokenizer.pad_token_id
        model.config.eos_token_id = self.tokenizer.eos_token_id
        
        # Decoder의 vocabulary 크기 조정 (CAD 토큰 추가 후)
        model.decoder.resize_token_embeddings(self.tokenizer.vocab_size)
        
        print(f"  Encoder params: {sum(p.numel() for p in model.encoder.parameters()):,}")
        print(f"  Decoder params: {sum(p.numel() for p in model.decoder.parameters()):,}")
        print(f"  Total params: {sum(p.numel() for p in model.parameters()):,}")
        
        return model
    
    def forward(
        self,
        pixel_values: torch.Tensor,
        labels: Optional[torch.Tensor] = None,
    ):
        """
        Forward pass.
        
        Args:
            pixel_values: 이미지 텐서 (B, C, H, W)
            labels: 타겟 토큰 ID (B, L)
        
        Returns:
            모델 출력 (loss, logits 등)
        """
        return self.model(
            pixel_values=pixel_values,
            labels=labels,
        )
    
    def generate(
        self,
        pixel_values: torch.Tensor,
        max_length: Optional[int] = None,
        num_beams: int = 4,
        temperature: float = 1.0,
        top_k: int = 50,
        top_p: float = 0.95,
        do_sample: bool = False,
    ) -> torch.Tensor:
        """
        이미지에서 JSON을 생성한다.
        
        Args:
            pixel_values: 이미지 텐서 (B, C, H, W)
            max_length: 최대 생성 길이
            num_beams: Beam search 빔 개수
            temperature: 생성 온도
            top_k: Top-k sampling
            top_p: Nucleus sampling
            do_sample: Sampling 사용 여부
        
        Returns:
            생성된 토큰 ID (B, L)
        """
        if max_length is None:
            max_length = self.config.max_length
        
        return self.model.generate(
            pixel_values=pixel_values,
            max_length=max_length,
            num_beams=num_beams,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
    
    def save_pretrained(self, save_directory: Path):
        """
        모델을 저장한다.
        
        Args:
            save_directory: 저장 디렉토리
        """
        save_directory = Path(save_directory)
        save_directory.mkdir(parents=True, exist_ok=True)
        
        # 모델 저장
        self.model.save_pretrained(save_directory)
        
        # 토크나이저 저장
        self.tokenizer.save_pretrained(str(save_directory))
        
        # 이미지 프로세서 저장
        self.image_processor.save_pretrained(save_directory)
        
        print(f"Model saved to {save_directory}")
    
    @classmethod
    def from_pretrained(
        cls,
        model_path: Path,
        config: Optional[VEDConfig] = None,
    ) -> "VEDModel":
        """
        저장된 모델을 로드한다.
        
        Args:
            model_path: 모델 경로
            config: 모델 설정 (None이면 기본값)
        
        Returns:
            VEDModel
        """
        if config is None:
            config = VEDConfig()
        
        # 토크나이저 로드
        tokenizer = CADTokenizer.from_pretrained(str(model_path))
        
        # 인스턴스 생성
        instance = cls.__new__(cls)
        instance.config = config
        instance.tokenizer = tokenizer
        
        # 이미지 프로세서 로드
        instance.image_processor = AutoImageProcessor.from_pretrained(model_path)
        
        # 모델 로드
        instance.model = VisionEncoderDecoderModel.from_pretrained(model_path)
        
        print(f"Model loaded from {model_path}")
        
        return instance
    
    def to(self, device: str):
        """모델을 디바이스로 이동한다."""
        self.model = self.model.to(device)
        return self
    
    def train(self):
        """학습 모드로 전환한다."""
        self.model.train()
    
    def eval(self):
        """평가 모드로 전환한다."""
        self.model.eval()

"""Vision Encoder-Decoder 모델 설정."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class VEDConfig:
    """
    Vision Encoder-Decoder 모델 학습 설정.
    
    Attributes:
        encoder_model: Vision encoder 모델명 (HuggingFace)
        decoder_model: Language decoder 모델명 (HuggingFace)
        image_size: 입력 이미지 크기
        max_length: 생성할 최대 토큰 수
        batch_size: 배치 크기
        learning_rate: 학습률
        num_epochs: 학습 에폭 수
        warmup_steps: Warmup 스텝 수
        weight_decay: Weight decay
        gradient_accumulation_steps: Gradient accumulation 스텝
        mixed_precision: Mixed precision 학습 (fp16/bf16)
        seed: Random seed
    """
    
    # 모델 설정
    encoder_model: str = "microsoft/swin-base-patch4-window7-224"
    # decoder_model: str = "gpt2"  # 1K 토큰 (기본)
    # decoder_model: str = "microsoft/Phi-3-mini-128k-instruct"  # 128K 토큰
    # decoder_model: str = "mistralai/Mistral-7B-Instruct-v0.2"  # 32K 토큰
    decoder_model: str = "gradientai/Llama-3-8B-Instruct-262k"  # 262K 토큰 (사용 중)
    
    # 데이터 설정
    image_size: int = 384  # Swin Transformer는 224의 배수 권장
    max_length: int = 131072  # JSON 최대 토큰 수 (128K, Llama-3-262k 기준)
    
    # 학습 설정
    batch_size: int = 1  # Long context는 메모리 많이 사용 (A100 40GB 권장)
    learning_rate: float = 5e-5
    num_epochs: int = 50
    warmup_steps: int = 500
    weight_decay: float = 0.01
    gradient_accumulation_steps: int = 16  # Effective batch size = 1 * 16 = 16
    
    # 최적화 설정
    mixed_precision: str = "fp16"  # "no", "fp16", "bf16"
    max_grad_norm: float = 1.0
    
    # 데이터 경로
    data_dir: Path = field(default_factory=lambda: Path("output"))
    train_file: str = "finetune_train.jsonl"
    val_file: str = "finetune_val.jsonl"
    
    # 토큰 제한 (데이터 필터링용)
    filter_max_tokens: int = 131072  # 이보다 긴 샘플은 제외 (Llama-3-262k 기준)
    
    # 체크포인트 설정
    output_dir: Path = field(default_factory=lambda: Path("output/ved_checkpoints"))
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 100
    save_total_limit: int = 3  # 최대 저장 체크포인트 수
    
    # 평가 설정
    eval_strategy: str = "steps"  # "no", "steps", "epoch"
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "eval_loss"
    
    # 재현성
    seed: int = 42
    
    # 기타
    num_workers: int = 4  # DataLoader workers
    use_wandb: bool = False  # Weights & Biases 사용 여부
    wandb_project: Optional[str] = "img2dwg-ved"
    
    def __post_init__(self):
        """경로를 Path 객체로 변환."""
        self.data_dir = Path(self.data_dir)
        self.output_dir = Path(self.output_dir)


@dataclass
class InferenceConfig:
    """
    추론 설정.
    
    Attributes:
        model_path: 학습된 모델 경로
        image_size: 입력 이미지 크기
        max_length: 생성할 최대 토큰 수
        num_beams: Beam search 빔 개수
        temperature: 생성 온도
        top_k: Top-k sampling
        top_p: Nucleus sampling
        device: 디바이스 ("cuda" 또는 "cpu")
    """
    
    model_path: Path = field(default_factory=lambda: Path("output/ved_checkpoints/best"))
    image_size: int = 384
    max_length: int = 2048
    
    # 생성 전략
    num_beams: int = 4  # Beam search (1이면 greedy)
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    do_sample: bool = False  # Beam search 사용 시 False
    
    # 디바이스
    device: str = "cuda"  # "cuda" 또는 "cpu"
    
    def __post_init__(self):
        """경로를 Path 객체로 변환."""
        self.model_path = Path(self.model_path)

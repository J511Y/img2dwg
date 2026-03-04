"""Vision Encoder-Decoder 모델 설정."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

TRAINING_METADATA_FILENAME = "ved_training_config.json"
MAX_LENGTH_HARD_LIMIT = 262_144
MAX_LENGTH_SOFT_LIMIT = 131_072


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
    max_length: int = MAX_LENGTH_SOFT_LIMIT  # JSON 최대 토큰 수 (128K, Llama-3-262k 기준)

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
    filter_max_tokens: int = MAX_LENGTH_SOFT_LIMIT  # 이보다 긴 샘플은 제외 (Llama-3-262k 기준)

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
    wandb_project: str | None = "img2dwg-ved"

    def __post_init__(self) -> None:
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
        max_length: 생성할 최대 토큰 수 (None이면 자동 결정)
        num_beams: Beam search 빔 개수
        temperature: 생성 온도
        top_k: Top-k sampling
        top_p: Nucleus sampling
        device: 디바이스 ("cuda" 또는 "cpu")
    """

    model_path: Path = field(default_factory=lambda: Path("output/ved_checkpoints/best"))
    image_size: int = 384
    max_length: int | None = None

    # 생성 전략
    num_beams: int = 4  # Beam search (1이면 greedy)
    temperature: float = 1.0
    top_k: int = 50
    top_p: float = 0.95
    do_sample: bool = False  # Beam search 사용 시 False

    # 디바이스
    device: str = "cuda"  # "cuda" 또는 "cpu"

    def __post_init__(self) -> None:
        """경로를 Path 객체로 변환."""
        self.model_path = Path(self.model_path)


@dataclass(frozen=True)
class MaxLengthResolution:
    """추론 max_length 결정 결과."""

    value: int
    source: str
    training_value: int | None
    warnings: list[str]


def _validate_max_length(value: int) -> int:
    if value <= 0:
        raise ValueError("max_length must be a positive integer")
    if value > MAX_LENGTH_HARD_LIMIT:
        raise ValueError(
            f"max_length={value} exceeds hard limit={MAX_LENGTH_HARD_LIMIT}. "
            "Use a smaller value or split inference input."
        )
    return value


def write_training_metadata(config: VEDConfig, output_dir: Path) -> Path:
    """학습 max_length 정책 메타데이터를 체크포인트 디렉토리에 기록한다."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "max_length": config.max_length,
        "filter_max_tokens": config.filter_max_tokens,
        "encoder_model": config.encoder_model,
        "decoder_model": config.decoder_model,
    }

    metadata_path = output_dir / TRAINING_METADATA_FILENAME
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return metadata_path


def load_training_max_length(model_path: Path) -> int | None:
    """체크포인트 메타데이터에서 학습 max_length 값을 로드한다."""
    model_path = Path(model_path)
    candidates = (
        model_path / TRAINING_METADATA_FILENAME,
        model_path.parent / TRAINING_METADATA_FILENAME,
    )

    for candidate in candidates:
        if not candidate.exists():
            continue

        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        max_length = data.get("max_length")
        if isinstance(max_length, int) and max_length > 0:
            return max_length

    return None


def resolve_inference_max_length(
    model_path: Path,
    cli_max_length: int | None,
    default_training_max_length: int = VEDConfig.max_length,
) -> MaxLengthResolution:
    """학습 정책 + CLI override를 기반으로 추론 max_length를 결정한다."""
    warnings: list[str] = []
    training_value = load_training_max_length(model_path)

    if training_value is not None:
        policy_default = training_value
        source = "checkpoint-metadata"
    else:
        policy_default = default_training_max_length
        source = "ved-default"
        warnings.append(
            "Training max_length metadata not found; fallback to VEDConfig.max_length."
        )

    if cli_max_length is not None:
        resolved = _validate_max_length(cli_max_length)
        source = "cli-override"

        if training_value is not None and cli_max_length != training_value:
            warnings.append(
                "CLI --max-length overrides checkpoint training max_length "
                f"({training_value} -> {cli_max_length})."
            )
    else:
        resolved = _validate_max_length(policy_default)

    if resolved > MAX_LENGTH_SOFT_LIMIT:
        warnings.append(
            "Configured max_length is very large; monitor GPU memory/OOM risk. "
            f"Recommended <= {MAX_LENGTH_SOFT_LIMIT} unless validated by benchmark."
        )

    return MaxLengthResolution(
        value=resolved,
        source=source,
        training_value=training_value,
        warnings=warnings,
    )

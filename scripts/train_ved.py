"""Vision Encoder-Decoder 모델 학습 스크립트."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from img2dwg.utils.logger import get_logger, setup_logging
from img2dwg.ved.config import VEDConfig
from img2dwg.ved.dataset import ImageToJSONDataset, collate_fn
from img2dwg.ved.model import VEDModel
from img2dwg.ved.tokenizer import CADTokenizer
from img2dwg.ved.utils import set_seed, get_device, print_gpu_memory


def main():
    """메인 학습 함수."""
    # 설정 로드
    config = VEDConfig()
    
    # 로깅 설정
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    setup_logging(log_level="INFO", log_file=log_dir / "train_ved.log")
    logger = get_logger(__name__)
    
    logger.info("=" * 80)
    logger.info("Vision Encoder-Decoder 학습 시작")
    logger.info("=" * 80)
    logger.info(f"Encoder: {config.encoder_model}")
    logger.info(f"Decoder: {config.decoder_model}")
    logger.info(f"Max Length: {config.max_length:,} 토큰")
    logger.info(f"Batch Size: {config.batch_size}")
    logger.info(f"Gradient Accumulation: {config.gradient_accumulation_steps}")
    logger.info(f"Effective Batch Size: {config.batch_size * config.gradient_accumulation_steps}")
    
    # Seed 설정
    set_seed(config.seed)
    logger.info(f"Random seed: {config.seed}")
    
    # 디바이스 설정
    device = get_device()
    logger.info(f"Device: {device}")
    if device == "cuda":
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        print_gpu_memory()
    
    # 토크나이저 초기화
    logger.info("토크나이저 초기화 중...")
    tokenizer = CADTokenizer(base_model=config.decoder_model)
    logger.info(f"Vocabulary size: {tokenizer.vocab_size:,}")
    
    # 데이터셋 로드
    logger.info("데이터셋 로드 중...")
    train_dataset = ImageToJSONDataset(
        jsonl_path=config.data_dir / config.train_file,
        tokenizer=tokenizer,
        image_size=config.image_size,
        max_length=config.max_length,
    )
    
    val_dataset = ImageToJSONDataset(
        jsonl_path=config.data_dir / config.val_file,
        tokenizer=tokenizer,
        image_size=config.image_size,
        max_length=config.max_length,
    )
    
    logger.info(f"Train samples: {len(train_dataset)}")
    logger.info(f"Val samples: {len(val_dataset)}")
    
    # DataLoader 생성
    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        collate_fn=collate_fn,
        pin_memory=True if device == "cuda" else False,
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        collate_fn=collate_fn,
        pin_memory=True if device == "cuda" else False,
    )
    
    logger.info(f"Train batches: {len(train_loader)}")
    logger.info(f"Val batches: {len(val_loader)}")
    
    # 모델 초기화
    logger.info("모델 초기화 중...")
    model = VEDModel(config=config, tokenizer=tokenizer)
    model = model.to(device)
    
    if device == "cuda":
        print_gpu_memory()
    
    # Optimizer 설정
    optimizer = torch.optim.AdamW(
        model.model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    
    # Learning rate scheduler
    total_steps = len(train_loader) * config.num_epochs // config.gradient_accumulation_steps
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=total_steps,
        eta_min=config.learning_rate * 0.1,
    )
    
    logger.info(f"Total training steps: {total_steps:,}")
    
    # 학습 루프
    best_val_loss = float("inf")
    global_step = 0
    
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    for epoch in range(config.num_epochs):
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Epoch {epoch + 1}/{config.num_epochs}")
        logger.info(f"{'=' * 80}")
        
        # Training
        model.train()
        train_loss = 0.0
        optimizer.zero_grad()
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1} [Train]")
        
        for batch_idx, batch in enumerate(progress_bar):
            pixel_values = batch["pixel_values"].to(device)
            labels = batch["labels"].to(device)
            
            # Forward pass
            outputs = model.forward(pixel_values=pixel_values, labels=labels)
            loss = outputs.loss / config.gradient_accumulation_steps
            
            # Backward pass
            loss.backward()
            
            train_loss += loss.item() * config.gradient_accumulation_steps
            
            # Gradient accumulation
            if (batch_idx + 1) % config.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(
                    model.model.parameters(),
                    config.max_grad_norm,
                )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1
                
                # 로깅
                if global_step % config.logging_steps == 0:
                    avg_loss = train_loss / (batch_idx + 1)
                    lr = scheduler.get_last_lr()[0]
                    logger.info(
                        f"Step {global_step}: loss={avg_loss:.4f}, lr={lr:.2e}"
                    )
                    if device == "cuda":
                        print_gpu_memory()
            
            progress_bar.set_postfix({"loss": loss.item() * config.gradient_accumulation_steps})
        
        avg_train_loss = train_loss / len(train_loader)
        logger.info(f"Epoch {epoch + 1} Train Loss: {avg_train_loss:.4f}")
        
        # Validation
        model.eval()
        val_loss = 0.0
        
        with torch.no_grad():
            progress_bar = tqdm(val_loader, desc=f"Epoch {epoch + 1} [Val]")
            
            for batch in progress_bar:
                pixel_values = batch["pixel_values"].to(device)
                labels = batch["labels"].to(device)
                
                outputs = model.forward(pixel_values=pixel_values, labels=labels)
                val_loss += outputs.loss.item()
                
                progress_bar.set_postfix({"loss": outputs.loss.item()})
        
        avg_val_loss = val_loss / len(val_loader)
        logger.info(f"Epoch {epoch + 1} Val Loss: {avg_val_loss:.4f}")
        
        # 체크포인트 저장
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            best_model_path = config.output_dir / "best"
            model.save_pretrained(best_model_path)
            logger.info(f"✅ Best model saved: {best_model_path} (val_loss={avg_val_loss:.4f})")
        
        # 주기적 체크포인트
        if (epoch + 1) % 10 == 0:
            checkpoint_path = config.output_dir / f"checkpoint-epoch-{epoch + 1}"
            model.save_pretrained(checkpoint_path)
            logger.info(f"Checkpoint saved: {checkpoint_path}")
    
    logger.info("\n" + "=" * 80)
    logger.info("학습 완료!")
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Best model: {config.output_dir / 'best'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

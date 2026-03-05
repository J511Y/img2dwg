# ruff: noqa: E402
"""VED 데이터셋 이미지 접근성/캐시 상태 사전 검증 스크립트."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.ved.dataset import ImageToJSONDataset, RemoteImagePolicy


class _NoopTokenizer:
    """이미지 프리플라이트 검증 전용 토크나이저 스텁."""

    def __call__(
        self,
        text: str,
        max_length: int,
        padding: str,
        truncation: bool,
        return_tensors: str,
    ) -> dict[str, torch.Tensor]:
        del text, padding, truncation, return_tensors
        return {"input_ids": torch.zeros((1, max_length), dtype=torch.long)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate/prefetch VED dataset images")
    parser.add_argument("--jsonl", type=Path, required=True, help="input jsonl path")
    parser.add_argument("--image-dir", type=Path, default=None, help="base dir for relative image paths")
    parser.add_argument("--cache-dir", type=Path, default=None, help="remote image cache directory")
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds")
    parser.add_argument("--max-retries", type=int, default=2, help="HTTP retry count")
    parser.add_argument("--backoff", type=float, default=0.5, help="retry backoff base seconds")
    parser.add_argument("--offline", action="store_true", help="allow only local files/cache")
    parser.add_argument("--limit", type=int, default=None, help="limit number of samples")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = RemoteImagePolicy(
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
        backoff_seconds=args.backoff,
        cache_dir=args.cache_dir,
        offline=args.offline,
    )
    dataset = ImageToJSONDataset(
        jsonl_path=args.jsonl,
        tokenizer=_NoopTokenizer(),
        image_dir=args.image_dir,
        image_size=32,
        max_length=16,
        remote_policy=policy,
    )

    total = len(dataset.samples)
    checked = 0
    failures = 0

    for sample in dataset.samples:
        if args.limit is not None and checked >= args.limit:
            break

        checked += 1
        image_url = sample["image_url"]
        try:
            dataset._load_image(image_url)
            print(f"[OK] {image_url}")
        except Exception as exc:  # pragma: no cover - CLI visibility
            failures += 1
            print(f"[FAIL] {image_url} :: {exc}")

    print("-" * 60)
    print(f"total_samples={total}")
    print(f"checked={checked}")
    print(f"failures={failures}")
    print(f"offline={args.offline}")
    print(f"cache_dir={dataset.remote_cache_dir}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

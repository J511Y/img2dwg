# web_image2cad_v1

Web에서 수집 가능한 공개 라이선스 JPG/PNG + DXF 후보 페어 벤치마크 매니페스트입니다.

## 포함 기준
- 라이선스가 명시된 공개 저장소의 원본 URL만 사용
- `image_sha256`, `dxf_candidate_sha256` 무결성 해시 고정
- 소스 추적 메타데이터(`source_repository`, `source_commit`, `license_spdx`, `license_url`) 필수

## 현재 구성 (2026-03-08)
- 총 **11개 case**
- 소스 저장소: `mozman/ezdxf` (MIT, pinned commit)
- 이미지 형식: JPG 2개, PNG 1개, JPEG 8개
- DXF 후보:
  - `images.dxf` (2개 case에서 공유)
  - `viewports.dxf` (1개 case)
  - `Graz_10km_3m.dxf` (8개 case에서 공유)

> `pairing_type`은 "ground truth"가 아니라, 동일 소스/동일 커밋 기반의 **DXF candidate 매칭 방식**을 명시합니다.

## 다운로드
```bash
uv run python scripts/fetch_web_benchmark_assets.py \
  --manifest eval/datasets/web_image2cad_v1/manifest.csv \
  --output-dir /tmp/img2dwg-web_image2cad_v1
```

스크립트는 `output_dir/images`, `output_dir/dxf_candidates` 하위로만 저장하며,
경로 순회(`..`, 절대경로, path separator 포함 filename) 입력을 즉시 차단합니다.

## 벤치마크 실행 예시
```bash
uv run python scripts/benchmark_strategies.py \
  --images /tmp/img2dwg-web_image2cad_v1/images \
  --dataset-id web_image2cad_v1-expanded \
  --git-ref "$(git rev-parse --short HEAD)" \
  --output /tmp/img2dwg-benchmark-web_image2cad_v1
```

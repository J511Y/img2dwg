# web_image2cad_v1

Web에서 수집 가능한 공개 라이선스 JPG/PNG + DXF 후보 페어 벤치마크 매니페스트입니다.

## 포함 기준
- 라이선스가 명시된 공개 저장소의 원본 URL만 사용
- `image_sha256`, `dxf_candidate_sha256` 무결성 해시 고정
- 소스 추적 메타데이터(`source_repository`, `source_commit`, `license_spdx`, `license_url`) 필수

## 다운로드
```bash
python scripts/fetch_web_benchmark_assets.py \
  --manifest eval/datasets/web_image2cad_v1/manifest.csv \
  --output-dir output/web_image2cad_v1
```

스크립트는 `output/images`, `output/dxf_candidates` 하위로만 저장하며,
경로 순회(`..`, 절대경로, path separator 포함 filename`) 입력을 즉시 차단합니다.

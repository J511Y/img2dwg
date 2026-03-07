# web_image2cad_v1 확장 평가 리포트 (2026-03-08)

## 1) 작업 요약
- eval 데이터셋 `web_image2cad_v1`를 **3 → 11 샘플**로 확장(+8)
- 확장된 eval 셋으로 전략 3종(`hybrid_mvp`, `consensus_qa`, `two_stage_baseline`) 재평가
- 결과 아티팩트(JSON/CSV) 생성

## 2) Eval 셋 확장 내역
매니페스트: `eval/datasets/web_image2cad_v1/manifest.csv`

- 총 샘플 수: **11**
- 소스: `mozman/ezdxf` (MIT)
- 고정 커밋: `c789459a42debe37e0be180fcccb2e1e54717942`
- 이미지 포맷 분포: JPG 2, PNG 1, JPEG 8
- DXF 후보 분포:
  - `images.dxf` 2건
  - `viewports.dxf` 1건
  - `Graz_10km_3m.dxf` 8건

라이선스/출처 문서:
- `eval/datasets/web_image2cad_v1/ATTRIBUTION.md`
- `eval/datasets/web_image2cad_v1/README.md`

## 3) 실행 커맨드 (재현 가능)
```bash
# 1) 매니페스트 기반 자산 다운로드 + SHA256 검증
uv run python scripts/fetch_web_benchmark_assets.py \
  --manifest eval/datasets/web_image2cad_v1/manifest.csv \
  --output-dir /tmp/img2dwg-web_image2cad_v1

# 2) 전략 벤치마크 실행
uv run python scripts/benchmark_strategies.py \
  --images /tmp/img2dwg-web_image2cad_v1/images \
  --dataset-id web_image2cad_v1-expanded \
  --git-ref "$(git rev-parse --short HEAD)" \
  --output /tmp/img2dwg-benchmark-web_image2cad_v1-expanded
```

## 4) 전략별 성능 비교 (expanded eval=11)
출처:
- `eval/reports/web_image2cad_v1_expanded/benchmark_summary.json` (run.git_ref=`0c1c953`)
- `eval/reports/web_image2cad_v1_expanded/strategy_comparison.csv`

| strategy | rank | composite | success_rate | cad_loadable_rate | mean_iou | mean_topology_f1 | median_ms | p95_ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| hybrid_mvp | 1 | 0.7006 | 1.0000 | 1.0000 | 0.7319 | 0.6596 | 53.11 | 70.29 |
| consensus_qa | 2 | 0.6738 | 1.0000 | 1.0000 | 0.6807 | 0.6034 | 52.20 | 76.34 |
| two_stage_baseline | 3 | 0.6503 | 1.0000 | 1.0000 | 0.6367 | 0.5534 | 52.69 | 69.91 |

## 5) 해석
- 품질 지표(`mean_iou`, `mean_topology_f1`) 기준으로 `hybrid_mvp`가 확장 셋에서도 1위 유지.
- 세 전략 모두 `success_rate=1.0`, `cad_loadable_rate=1.0`으로 안정성은 동일.
- 속도(`median_ms`)는 세 전략 차이가 작고, `p95_ms`는 `consensus_qa`가 상대적으로 높음.

## 6) 한계 / 다음 단계
- 현재 페어는 `DXF candidate` 기반이며, strict ground-truth 1:1 정답셋은 아님.
- geo 샘플 8건은 하나의 공유 DXF 후보(`Graz_10km_3m.dxf`)를 사용.
- 다음 확장 제안:
  1. 소스 다양화(다른 공개 라이선스 저장소)로 도메인 편향 완화
  2. true paired GT(이미지-정답 DXF 1:1) 비중 확대
  3. 샘플 난이도 태깅(도면 복잡도/노이즈 수준) 추가

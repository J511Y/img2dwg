# web_floorplan_grid_v1

웹 공개 소스(라이선스 명시)에서 수집한 **floorplan형 래스터 이미지** 기반 회귀 진단 데이터셋입니다.

목적은 정답 DXF와의 정량 비교보다, 다음과 같은 **출력 이상 징후**를 자동 감지하는 것입니다.

- DXF 로드 불가 / 비어있는 출력
- 엔티티 수 과소(너무 단순한 출력)
- 엔티티 타입 다양성 부족
- 축 정렬 선분 반복 + 좌표 다양성 부족으로 인한 grid-like 패턴 의심

## 구성

- 샘플 수: 12
- 소스 패밀리: Wikimedia Commons (Category:Floor plans of office buildings)
- 라이선스: Public domain (manifest에 파일별 증빙 URL 고정)

## 파일

- `manifest.csv`: 샘플 URL/해시/출처/라이선스 증빙 메타데이터
- `ATTRIBUTION.md`: 소스/라이선스 정책 및 증빙 방식

## 다운로드

```bash
uv run python scripts/fetch_web_floorplan_assets.py \
  --manifest eval/datasets/web_floorplan_grid_v1/manifest.csv \
  --output-dir output/web_floorplan_grid_v1
```

## 회귀 실행

```bash
uv run python scripts/run_grid_artifact_regression.py \
  --manifest eval/datasets/web_floorplan_grid_v1/manifest.csv \
  --assets-dir output/web_floorplan_grid_v1 \
  --benchmark-output output/benchmark/web_floorplan_grid_v1 \
  --dataset-id web_floorplan_grid_v1 \
  --git-ref "$(git rev-parse HEAD)"
```

리포트 기본 출력:

- JSON: `eval/reports/web_floorplan_grid_v1/grid_artifact_regression.json`
- Markdown: `eval/reports/web_floorplan_grid_v1/grid_artifact_regression.md`

# 실험 증거 계약

## run 디렉터리 (Git 외부)

```text
<private-output-root>/<run-id>/
  run-manifest.json
  config.snapshot.json
  logs/
  metrics.json
  per-sample-results.csv
  cad-ir/ + dxf/ + dwg/
  previews/ + failures/
  source-output-manifest.json
  receipt.json
```

현재는 구조 계약이며 해당 산출물은 생성되지 않았다. run ID는 날짜·후보 ID·고유 suffix를 포함한다. 초기 manifest는 planned, 실행시 running, 종료시 succeeded/failed/blocked와 실제 시작·종료시각을 기록한다. partial result와 전체 성공을 분리한다.

## 재현 필드

Git SHA/dirty snapshot, 모델 repo+revision/checkpoint hash 또는 provider snapshot, SDK/런타임/GPU/드라이버, 입력 dataset manifest/split hash, annotation·정합 버전, seed, prompt·question schema hash, 모든 해상도/tile/threshold·좌표/단위, writer/converter/CAD app 버전, 실행 명령, metric 구현 revision, 예산·실제 비용·retry, source/output SHA-256.

실패 sample ID, traceback/exit code/timeout, 제외 사유·분모를 보존한다. receipt에는 검사별 pass/fail/not-run과 실제 검증 시각을 기록한다. 모델 confidence는 기하·CAD 검사를 대체하지 않는다. 원자료가 가변이면 snapshot/hash를 고정하기 전 확정 성능을 쓰지 않는다.

## 연구노트 연결

공개 `docs/experiments/`에는 비식별 서술과 근거 ID, 비공개 번들은 중앙 연구노트에 연결한다. 중요한 실험은 기술적 불확실성→가설→방법→실패 포함 결과→해석→다음 실험을 이어서 작성한다. 주간/월간 `.md`+실행 `.ipynb`+bundle/manifest/receipt는 중앙 작업에서 생성한다. 문헌조사·셋업에 실험 이미지나 성능 숫자를 만들어 넣지 않는다.

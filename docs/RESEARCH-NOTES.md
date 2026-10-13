# 중앙 연구노트 연결

이 프로젝트는 기존 사내 연구노트 워크스페이스의 `projects.json`에 `img2dwg`로 등록한다. 중앙 실제 경로와 예약 ID는 사내 로컬 설정/기록에서 확인한다. 공개 repo에는 고객 원본과 내부 경로를 쓰지 않는다.

## 주간·월간 수집

- 주간: 기존 월요일 08:30 KST, 직전 완결 월~일.
- 월간: 기존 매월 1일 10:30 KST, 직전 완결 달.
- 수집 대상: Git 이력, `docs/experiments/`, `docs/STATUS.md`, 조사/결정/백로그, private run manifest·metrics·CAD receipt·render-back·실패·hash.
- 월간은 주간의 성공 receipt와 동일 protocol 결과를 합성하며 주간 누락 성과를 추정하지 않는다.
- 기존 `data-pipeline`의 동일 페어/실험을 참조하면 출처를 유지하고 성과를 이중 계상하지 않는다.

## 산출물과 분류

중앙에서 `weekly/YYYY-Www.md` / `monthly/YYYY-MM.md`와 같은 이름의 실제 실행 `.ipynb`, `assets/{kind}/{period}/`의 bundle·manifest·notebook receipt를 작성한다. private artifact location을 공개 본문에 노출하지 않고 식별자를 제거한 원자료만 포함한다.

초기 셋업·문헌조사는 연구지원/연구 준비 활동이다. 기술적 불확실성·가설·실행·비교·실패·해석·다음 실험의 증거가 있을 때 R&D 핵심/후보로 판단한다. backlog planned 항목을 실행 성과로 기록하지 않는다. 없는 image/metric/code evidence는 0 또는 미확보로 기록한다.

예약 연결 자체와 미래 연구노트 실행 성공은 구분한다. 신규 프로젝트는 2026-10-13부터 수집 대상이며 과거 기간에 새 활동이 있었다고 소급하지 않는다. 예약 실행시 local config가 없거나 접근이 끊겼으면 조사 가능한 범위와 확인 필요를 기록한다.

2026-10-13 데이터 확장은 [v0.2 릴리스](research/2026-10-13-dataset-v02-release.md)와 비식별 집계 JSON, private remote-readback receipt를 수집한다. 데이터 준비/버킷 byte 검증을 모델 성능이나 학습 성공으로 분류하지 않는다.

# 에이전트 작업 지침

## 시작 순서

1. 이 파일, `README.md`, `docs/STATUS.md`, `docs/PROJECT.md`, `docs/DECISIONS.md`, `docs/harness/workflow.md`를 읽는다.
2. `git status --short --branch`, 원격, 관련 변경을 확인하고 기존 작업을 보존한다.
3. 작업에 따라 `docs/DATA.md`, `docs/CAD.md`, `docs/EVALUATION.md`, 조사·백로그를 읽는다.
4. 목표·완료 조건·미확인 사항을 짧게 알리고 현재 요청 범위에서 수행한다.

## 현재 권한과 범위

- 현재 사용자는 원본을 보존한 데이터셋 pilot 구축·30~50개 샘플 추출·치수/정합 검사·검수 화면 구현을 허용했다. 모델 학습·유료 API·운영 배포는 시작하지 않았다. 현재 실행 방법과 결과는 `docs/harness/dataset-pilot.md`, `docs/experiments/2026-10-13-EXP-029-pilot.md`를 읽는다.
- 후속 사용자가 구현·실험을 요청하면 해당 범위로 진행한다. 이 초기 상태를 영구적인 구현 금지로 해석하지 않는다.
- 데이터 수집·변경전 crop·ODA roundtrip·치수/정합 검증 실행기가 추가됐다. 학습/배포 하네스·CI·canonical CAD-IR schema validator와 구분한다.
- 사내 워크의 의뢰 연결 경로가 데이터 위치의 정본이다. 원본 폴더를 읽기 전용으로 사용하고 결과는 별도 run 폴더에 작성한다. 원본 DWG를 덮어쓰지 않는다.
- 실제 경로는 `configs/paths.local.json`, 로컬 조사 결과는 `local/`에 둔다. 둘 다 Git 제외다. 비밀은 환경 변수 또는 비밀 저장소에서 읽고 출력하지 않는다.
- 다른 저장소는 기본적으로 조사만 한다. 기존 `data-pipeline`·모델 저장소의 dirty 변경을 가져오거나 수정·커밋하지 않는다. 재사용할 때 출처 revision/hash와 라이선스를 기록한다.

## 연구·검증 규칙

- 목표는 편집 가능한 실제 DWG다. CAD-IR→DXF→DWG→실제 CAD 열기/수정/저장→render-back까지 구분해 증명한다.
- 현재 적용 전략은 `docs/research/2026-10-13-domain-reassessment.md`다. Jippin 원본 픽셀 오버레이와 canonical CAD 좌표·치수·간격 복원을 구분한다. 사내 CAD geometry와 직원 확정 wall semantics를 연결하고, generic wall/기타벽을 비내력 정답으로 승격하지 않는다. 사내 데이터 학습 필요성과 모든 weight의 scratch 학습 필요성을 구분한다.
- 사용자 추가 설계 계약은 `docs/research/2026-10-13-closed-loop-hitl-design.md`다. 주력 데이터는 같은 의뢰 폴더의 준공도면+변경전후.dwg이고 target은 검수된 변경전 평면 영역이다. thumbnail/왼쪽 위치만으로 CAD crop 정답을 확정하지 않는다. System-1은 두 이미지 기반 다음 CAD action controller 구상까지 포함하며 현재 Jev/Laya의 text/JSON 기능과 별도 vision policy를 구분한다. HITL 중간 수정·잠금·undo/resume을 정상 성공 경로로 설계한다.
- 좌표 변환·원점·y축·단위·축척·문 방향·레이어를 명시한다. 비직교 벽과 곡선을 무조건 직각화하지 않는다.
- 프론티어, Jev/Laya System-1, 고전 기하, segmentation, graph, sequence, JEPA, diffusion, hybrid 후보를 배제하지 않고 백로그에 등록한다. 명칭·입력 모달리티·실제 가용성을 출처로 확인한다.
- 동일 의뢰/건물/동일 평면 계열과 augmentation은 split 간 섞지 않는다. 테스트 자료로 프롬프트·threshold·routing을 튜닝하지 않는다.
- 성능 주장에는 데이터/split/hash, 표본수, metric 구현, 모델 revision, seed, 해상도, CAD 엔진, 비용·재시도 포함 조건과 원자료를 붙인다. 학습 loss·커밋·문헌 수치를 우리 성능으로 쓰지 않는다.
- schema 및 기하 검사 실패는 모델 confidence로 통과시킬 수 없다. System-1은 결정론적 검증을 보조한다.
- planned/running/succeeded/failed/blocked/rejected 상태를 구분하고 실패 로그와 다음 실험을 남긴다. 실패 실행을 succeeded로 재작성하지 않는다.
- 모델 카드의 zero-shot·보정·속도 주장은 해당 출처의 측정으로 표시하고 사내 데이터에서 재검증한다.
- 연구노트는 `$koita-research-notebook`, 증거 번들은 `$research-note-evidence-assets`를 적용한다. 중앙 `projects.json`과 주간·월간 프롬프트가 수집 정본이다. 셋업·문헌조사를 실험 성공으로 승격하지 않는다.

## 완료와 인계

변경 범위에 맞는 검증만 수행하고 실제 결과를 보고한다. 구현 시 meaningful unit/integration/CAD roundtrip 체크를 추가한다. 원본·고객정보·비밀이 Git에 포함되지 않았는지 확인한다. `docs/STATUS.md`, 필요시 결정/백로그/실험 기록을 갱신한다. 수정 파일, 검증, 남은 불확실성·다음 재현 방법을 짧게 전달한다.

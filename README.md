# img2dwg

평면도 이미지에서 **CAD에서 열고 편집할 수 있는 DWG**를 복원하는 모델·파이프라인 연구 프로젝트.

최신 결과: [EXP-054](docs/experiments/2026-10-15-EXP-054-full-continuation.md)의 실제1,028페어
본학습을 완료했다. **기존10 재현은 유지됐지만 신규 도면 복원은 실패해 배포하지 않았다.**

| 고정 후보 fresh CPU 검사 | pass | 필수 치수 값·실제 길이 |
| --- | ---: | ---: |
| 기존 TRAIN10 | 10/10 | 252/252 |
| 별도 정정20 | 0/20 | 0/479 |

21,928 update 후 품질 정체로 종료했고 개발 지표로 고른1420 update best를 검증했다.
검증 모델 전체를 동결한 새268만 parameter pooled residual 학습이며 전체 모델 fine-tuning은 아니다.
30개 직접 검수, 원본 pixel 검사, native DXF와 기존10 DWG 재열기·브라우저 다운로드를 확인했다.
[비교 화면](http://127.0.0.1:8781/full-continuation-review.html)은30개 전체를 제공한다.
[학습 loss와 복원 품질](docs/research/assets/2026-10-15-full-continuation-learning.svg)을 구분한다.
검증20은 학습 전 pixel 중복1건을 교체한 기존19+신규1로 옛20의476개와 다른479개 치수다.

현재 [private Space](https://huggingface.co/spaces/youjunhyeok/img2dwg)는 기존에 승인된
**five-case pilot**이며 이번 source6ca23df9…/full 후보aed6d0e8…로 교체하지 않았다.
Space는 확대 가능한 SVG·편집 가능한 native DXF를 제공하며 직접 DWG 다운로드는 미구현이다.
이번 로컬 비교 화면의 기존10 DWG 다운로드와 혼동하지 않는다.

이전 실험: [EXP-053 TRAIN10 재현](docs/experiments/2026-10-14-EXP-053-ranked-consistent-decoder.md),
[EXP-046 공유 노드·컴포넌트 학습](docs/experiments/2026-10-14-EXP-046-shared-decoder.md),
[과거 full-v1 회고](docs/research/2026-10-14-experiment-retrospective.md),
[첫 합성 baseline](docs/experiments/2026-10-13-EXP-043-vector-first.md).
각 실행의 모델·데이터·품질·배포 상태를 구분한다. 아래는 프로젝트의 지속 목표다.

사내 input/output 1,383개와 변경전/native CAD는 private HF img2dwg bucket에 저장하고
전체 원격 해시 검증을 마쳤다. [데이터 릴리스](docs/research/2026-10-13-dataset-v02-release.md),
[재실행 안내](docs/harness/dataset-release.md).

## 목표와 기본 경로

사내 워크 의뢰에 연결된 원본 이미지와 DWG를 읽기 전용으로 활용한다. 동일 의뢰 폴더 페어는 사용자 확정 근거로 수집하고 변경전 추출·컴포넌트·단위·무결성을 전처리한다. 실제 학습/평가는 label coverage와 split 상태에 맞춰 수행한다.

```text
의뢰별 이미지 + 검수된 DWG 페어
  → 이미지 정규화 / OCR / 인식
  → 벡터 엔티티·위상·치수 후보 (CAD-IR)
  → 기하·위상·단위 검증
  → 결정론적 DXF 작성 → DWG 변환
  → CAD 재열기·편집·저장 + render-back + 사람 검수
```

벽·문·창·방·치수의 편집 가능성과 기하 일치도를 평가한다. DXF 생성만으로 DWG 완료를 선언하지 않는다. 축척을 확인하지 못하면 `unknown`으로 남기며 절대 치수를 추정해 확정하지 않는다.

## 문서 지도

| 문서 | 역할 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | 다음 세션의 진입점, 작업 범위와 증거 규칙 |
| [프로젝트 목표](docs/PROJECT.md) | 범위·성과 기준·기술적 불확실성 |
| [로드맵](docs/ROADMAP.md) | 단계별 통과 기준과 당장 할 일 |
| [데이터 계약](docs/DATA.md) | 워크 의뢰 폴더, 페어 검수, split·개인정보 |
| [CAD 출력 계약](docs/CAD.md) | CAD-IR, 좌표·엔티티·DWG 검증 |
| [평가 프로토콜](docs/EVALUATION.md) | 기하·위상·호환성·비용 비교 |
| [작업 하네스](docs/harness/workflow.md) | 시작→설계→실험→검증→인계 절차 |
| [실험 증거 계약](docs/harness/evidence.md) | run manifest·실패·receipt |
| [조사 보고서](docs/research/2026-10-13-survey.md) | 데이터셋·모델·최근 트렌드·출처 |
| [사내 자산 기반 재조사](docs/research/2026-10-13-domain-reassessment.md) | Jippin·검수 라벨·HF·CAD 자산과 정밀 복원 학습 전략 |
| [반복 그리기·HITL 설계](docs/research/2026-10-13-closed-loop-hitl-design.md) | System-1 controller, 준공도면–변경전 target, 중간 개입 |
| [실험 백로그](docs/research/experiment-backlog.md) | 시도할 접근법과 개별 가설 |
| [결정 기록](docs/DECISIONS.md) | 현재 결정·근거·재검토 조건 |
| [연구노트 연결](docs/RESEARCH-NOTES.md) | 기존 주간·월간 예약 수집 계약 |
| [현재 상태](docs/STATUS.md) | 완료·미실행·다음 작업 |
| [실험 리뷰](docs/research/2026-10-14-experiment-retrospective.md) | 목표 대비 진척, 실행별 실패, 초기화 대조, 판단 회고 |

설정은 [configs/paths.example.json](configs/paths.example.json), [configs/harness.json](configs/harness.json), 실험 기록은 [templates/experiment.md](templates/experiment.md)와 [templates/run-manifest.example.json](templates/run-manifest.example.json)에서 시작한다. 실제 경로 설정과 원자료는 Git에 넣지 않는다.

## 연구 방향

프론티어 VLM, 고전 기하, 세그멘테이션, 그래프·폴리곤 시퀀스, 자기지도 인코더, diffusion/flow, 증류, System-1 Jev/Laya를 넓게 비교한다. Jev/Laya는 텍스트·JSON 상태의 선택/점수/확률 판단 후보이며 이미지→DWG 생성기로 가정하지 않는다. 모든 후보는 `planned`부터 시작하고 실패·보류·제외 사유도 기록한다.

실제 데이터·원본 도면·가중치·실행 산출물·고객정보는 외부 저장소에서 관리한다. 이 공개 저장소에는 문서, 향후 코드, 비식별 예제만 저장한다. 코드·데이터·가중치의 라이선스는 각각 확인하며 프로젝트 자체의 공개 이용허락 라이선스는 아직 결정하지 않았다.

최신 실행 정본은 [벡터 우선 학습 계획](docs/research/2026-10-13-vector-first-training-plan.md)이다. 첫 주력 DINOv3+graph decoder, 비교 Raster2Seq와 치수 OCR/association/solver로 입력→편집 가능한 DWG를 우선한다. 반전은 CAD/후속 편집이며 전체 특징점 정합은 중단했다.

첫 학습 정답의 단위는 [CAD 컴포넌트 구조 감사](docs/research/2026-10-13-component-supervision-audit.md)를 따른다. 원래 블록·치수 객체와 분해된 업무 컴포넌트를 확인하고 catalog/factory를 검증한 뒤 학습한다.

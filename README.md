# img2dwg

평면도 이미지에서 **CAD에서 열고 편집할 수 있는 DWG**를 복원하는 모델·파이프라인 연구 프로젝트.

현재 단계: **1,028개 실제 페어 본학습은 완료했으나 구조·치수 복원은 실패했다.**
본학습 선택 모델은 원래 5개 0/5·치수 0/112, 별도 20개 0/20·치수 0/476이다.
20개를 직접 시각 검수했고 Space에 교체하지 않았다. 추가 실험을 중단하고
[상세 실험 리뷰](docs/research/2026-10-14-experiment-retrospective.md)를 작성했다.

현재 private Space는 앞서 승인된 **5개 재현 실험 모델**이다.
GPU 재현은 5/5·치수 112/112, CPU 서빙 재현은 4/5·치수 112/112다.
별도 CPU 20개 검증은 0/20이므로 Space에는 사용자가 승인한 **5개 재현 실험 모델**로
표시한다. 이 모델과 실패한 본학습 모델을 구분하며 일반화 성공을 주장하지 않는다.
[EXP-046](docs/experiments/2026-10-14-EXP-046-shared-decoder.md),
[공유 노드 학습 하네스](docs/harness/shared-graph-training.md).
Space는 실제 모델의 raster-free SVG·native BLOCK/INSERT와 DIMENSION을 갖는 DXF를
반환한다. 선택 100mm 보정과 보정 전 결과/기록을 제공한다. 직접 DWG 다운로드는 미구현이다.

이전 기록: **첫 좌표 모델은 실제 준공도면 복원에 실패해 기본 서비스 출력에서 제외했다.**
실제 페어 5개 학습/20개 검증 모델도 구조·치수 기준을 통과하지 못했다.
[컴포넌트 출력 설계 정정](docs/research/2026-10-14-component-decoder-correction.md)을 적용하며,
primitive head의 후속 학습은 중단했다. 이후 구현·학습은 EXP-046이 대체한다.
[실패 분석](docs/experiments/2026-10-13-EXP-044-real-scan-failure.md).
[Space](https://huggingface.co/spaces/youjunhyeok/img2dwg)의 이전 관측 선 검출 기준선은
학습 모델의 CAD 복원 결과가 아니었다. 당시 실패 결과와 실행 기록은 보존한다.

첫 실험의 당시 기록: DINOv3 벡터 좌표 모델 학습과 비공개 inference Space를 연결했다.
[Space](https://huggingface.co/spaces/youjunhyeok/img2dwg)에서 전유부를 잘라 업로드하고
확대 가능한 SVG·편집 가능한 DXF 초안을 확인한다. HF 소유 계정 로그인이 필요하다.
CAD 합성 train 1,028개/validation 128개, full 2,500 steps.
합성 validation 선분 F1 0.396이며 실제 입력의 정밀도·치수 완전성·직접 DWG 다운로드는
아직 완료하지 않았다. [실험 결과](docs/experiments/2026-10-13-EXP-043-vector-first.md),
[학습/배포 하네스](docs/harness/vector-training.md)를 참조한다.

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

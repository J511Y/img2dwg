# img2dwg

평면도 이미지에서 **CAD에서 열고 편집할 수 있는 DWG**를 복원하는 모델·파이프라인 연구 프로젝트.

현재 단계: **2026-10-13 기본 세팅·문헌 조사 완료, 모델/변환/학습 코드 미구현**. 데이터 수, 성능, CAD 호환성은 아직 실측하지 않았다.

## 목표와 기본 경로

사내 워크 의뢰에 연결된 원본 이미지와 DWG를 읽기 전용으로 활용한다. 대응 이미지–DWG의 동일 평면·변경 전후·좌표 정합을 검수한 뒤 학습/평가 자료로 사용한다.

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

설정은 [configs/paths.example.json](configs/paths.example.json), [configs/harness.json](configs/harness.json), 실험 기록은 [templates/experiment.md](templates/experiment.md)와 [templates/run-manifest.example.json](templates/run-manifest.example.json)에서 시작한다. 실제 경로 설정과 원자료는 Git에 넣지 않는다.

## 연구 방향

프론티어 VLM, 고전 기하, 세그멘테이션, 그래프·폴리곤 시퀀스, 자기지도 인코더, diffusion/flow, 증류, System-1 Jev/Laya를 넓게 비교한다. Jev/Laya는 텍스트·JSON 상태의 선택/점수/확률 판단 후보이며 이미지→DWG 생성기로 가정하지 않는다. 모든 후보는 `planned`부터 시작하고 실패·보류·제외 사유도 기록한다.

실제 데이터·원본 도면·가중치·실행 산출물·고객정보는 외부 저장소에서 관리한다. 이 공개 저장소에는 문서, 향후 코드, 비식별 예제만 저장한다. 코드·데이터·가중치의 라이선스는 각각 확인하며 프로젝트 자체의 공개 이용허락 라이선스는 아직 결정하지 않았다.

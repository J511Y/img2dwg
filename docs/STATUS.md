# 현재 상태 · 2026-10-13 KST

## 완료한 기본 세팅

- empty GitHub repo를 현 폴더로 clone하고 목표·README·AGENTS·선택/검증 기준을 구성했다.
- 데이터/CAD/평가 계약, 선언적 harness 설정, 실험·run manifest·PR/issue 양식을 추가했다.
- 공식 논문·repo·model card 기반 조사 보고서와 22개 planned 실험 백로그를 작성했다.
- Jev/Laya의 공식 System-1 계약과 HF Laya 모델·demo Space를 확인했다. JEPA/LLaDA와 구분했다.
- 워크 설정의 입력 루트 접근과 로컬 ODA 설치를 확인했다. 실제 설정·비공개 조사 상세는 `local/`에 보관한다.
- 기존 data-pipeline 페어 DWG 10개 header를 소량 읽었으며 모두 `AC1032`였다. 업무 전체 버전 분포나 목표 버전을 확정하는 표본은 아니다.
- 중앙 연구노트 지도에 7번째 프로젝트로 등록하고 기존 주간·월간 예약 prompt를 갱신했다. 정규화 prompt 일치·기존 주기/모델/프로젝트 보존을 확인했다.

## 초기 세팅 시점의 미실행과 불확실성

모델/변환/학습 코드, 실행 하네스/CI, 데이터 전체 스캔·페어 승인·split, dataset 다운로드·GPU/API 호출, DWG 생성·실제 CAD 열기/수정/저장, metric 측정·배포는 미실행이다. 설치 확인은 CAD 호환성 검증이 아니다.

target CAD·DWG version, usable pair 수·정합·권리·외부처리, 예산, metric threshold, 프로젝트 라이선스는 확인 필요다. 과거 data-pipeline 작업 트리는 재현 검증 전 성과로 승계하지 않는다.

## 사용자 추가 맥락 재조사 · 2026-10-13

[사내 자산 기반 보고서](research/2026-10-13-domain-reassessment.md)를 추가했다. Jippin 소비 코드·직원 확정 라벨·가공 manifest·HF endpoint 설정·기존 CAD-IR 보고 JSON을 읽기 전용으로 확인했다. 새 모델 실행·DWG 변환은 하지 않았다. 현재 후보 backlog는 28개이며 초기 22개 목록에 joint gold·dimension solver·dewarp·사내 학습 대조를 추가했다. 공개 후보 목록보다 사내 geometry/semantics 감독과 정밀도 계약을 우선한다.

## 반복 그리기·HITL·페어 조건 추가 · 2026-10-13

[사용자 구상 설계](research/2026-10-13-closed-loop-hitl-design.md)를 작성했다. 원본+현재 CAD render에서 다음 drawing action을 판단하는 세 후보, 준공도면+변경전후.dwg의 변경전 target, final CAD→합성 action trajectory, 중간 사람 수정·잠금·undo/resume을 반영했다. 후보는 34개다. 첨부 thumbnail과 기존 crop 코드를 읽었으며 원본 재추출·모델 실행은 하지 않았다.

## 다음 구현 작업

## 데이터 pilot 실행 완료 · 2026-10-13

[EXP-029](experiments/2026-10-13-EXP-029-pilot.md): 운영 의뢰 인덱스 기반으로 조건에 맞는 후보 60개를 찾고 40개 변경전 DXF/DWG를 추출·ODA 재열기했다. DIMENSION 913개 보존 pass, 원본 80개 hash/size/mtime 보존 확인. 자동 정합은 weak/degenerate 38·신뢰할 match 없음 2로 자동 승인 0이다. 최종 entity duplicate 0, header/loader warning 3을 기록했다. 모델 학습·직원 승인·gold split은 미실행이다.

수집/검수 runner와 비공개 HTML 비교 화면, 실제 실행 report notebook·manifest/receipt를 추가했다. [실행 안내](harness/dataset-pilot.md), private output 위치는 `configs/paths.local.json`을 참조한다. 직원은 비교 화면에서 before 영역·정합·치수·대응점과 메모를 검수하고 JSON으로 내보낼 수 있다.

다음은 입력 ROI/대응점과 변경상태 승인, 종이 휨·도면 차이 분리, 3개 header/loader warning 진단이다. 승인되지 않은 40개를 학습에 투입하지 않는다. 실제 CAD UI의 수정·저장은 별도 확인한다.

## 최신 방향 수정

사용자 요청으로 전체 특징점 정합 재시도를 중단하고 기존 결과를 보존했다. 다대일 대응 방지·양방향/양쪽 공간 분포 검사를 추가했고 단위 테스트 9개를 통과했으나 실제 40개 재정합은 하지 않았다.

다음은 기존 40개 중 5개의 전유부/변경전/실제 방향 검수와 치수 원장·중심선 GT 구축이다. 승인 치수에 맞는 geometry 기준선 → 비교 UI → 40개 확대 → 모델 실험 순으로 진행한다. 원장/solver/새 UI·직원 승인·학습은 미실행이다. 이전 913개 보존 pass는 입력 치수 완전성/실제 길이 검증이 아니다. [최신 계획](research/2026-10-13-exclusive-unit-dimension-plan.md)이 앞선 다음 작업 순서를 대체한다.

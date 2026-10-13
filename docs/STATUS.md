# 현재 상태 · 2026-10-13 KST

## 완료한 기본 세팅

- empty GitHub repo를 현 폴더로 clone하고 목표·README·AGENTS·선택/검증 기준을 구성했다.
- 데이터/CAD/평가 계약, 선언적 harness 설정, 실험·run manifest·PR/issue 양식을 추가했다.
- 공식 논문·repo·model card 기반 조사 보고서와 22개 planned 실험 백로그를 작성했다.
- Jev/Laya의 공식 System-1 계약과 HF Laya 모델·demo Space를 확인했다. JEPA/LLaDA와 구분했다.
- 워크 설정의 입력 루트 접근과 로컬 ODA 설치를 확인했다. 실제 설정·비공개 조사 상세는 `local/`에 보관한다.
- 기존 data-pipeline 페어 DWG 10개 header를 소량 읽었으며 모두 `AC1032`였다. 업무 전체 버전 분포나 목표 버전을 확정하는 표본은 아니다.
- 중앙 연구노트 지도에 7번째 프로젝트로 등록하고 기존 주간·월간 예약 prompt를 갱신했다. 정규화 prompt 일치·기존 주기/모델/프로젝트 보존을 확인했다.

## 미실행과 불확실성

모델/변환/학습 코드, 실행 하네스/CI, 데이터 전체 스캔·페어 승인·split, dataset 다운로드·GPU/API 호출, DWG 생성·실제 CAD 열기/수정/저장, metric 측정·배포는 미실행이다. 설치 확인은 CAD 호환성 검증이 아니다.

target CAD·DWG version, usable pair 수·정합·권리·외부처리, 예산, metric threshold, 프로젝트 라이선스는 확인 필요다. 과거 data-pipeline 작업 트리는 재현 검증 전 성과로 승계하지 않는다.

## 사용자 추가 맥락 재조사 · 2026-10-13

[사내 자산 기반 보고서](research/2026-10-13-domain-reassessment.md)를 추가했다. Jippin 소비 코드·직원 확정 라벨·가공 manifest·HF endpoint 설정·기존 CAD-IR 보고 JSON을 읽기 전용으로 확인했다. 새 모델 실행·DWG 변환은 하지 않았다. 현재 후보 backlog는 28개이며 초기 22개 목록에 joint gold·dimension solver·dewarp·사내 학습 대조를 추가했다. 공개 후보 목록보다 사내 geometry/semantics 감독과 정밀도 계약을 우선한다.

## 다음 구현 세션

[로드맵](ROADMAP.md)의 P1: 의뢰 연결 인덱스 기반 소량 페어 감사와 P2: GT CAD writer roundtrip부터 시작한다. 구현 요청이 오면 현재 선언적 계약을 실제 validator/runner로 확장한다.

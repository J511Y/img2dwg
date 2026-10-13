# 단계별 연구 로드맵

모든 모델 계열을 탐색하되 데이터·writer 검증과 후보 실행을 분리한다. 실험 상태는 [백로그](research/experiment-backlog.md)에 기록한다.

| 단계 | 산출물 | 다음 단계 통과 기준 | 현재 |
| --- | --- | --- | --- |
| P0 기본 세팅 | 목표·AGENTS·하네스·문헌·예약 연결 | 문서/JSON/링크 검증, 중앙 수집 등록 | 완료 |
| P1 데이터 감사 | 비공개 의뢰 인덱스, 페어 manifest, 정합·권리 검수 | 동일 평면/상태 확인, 중복 그룹·split 고정, 검수 제외 사유 | 40개 pilot 추출·자동 검사 완료, 정합/사람 검수 미통과 |
| P2 CAD 기준선 | 검수 GT CAD-IR, writer roundtrip, render 설정 | GT→DWG 재열기·수정·저장·재열기, 단위/레이어/geometry 검사 | ODA crop roundtrip·치수 보존 검사 완료, canonical/실제 CAD 수정·저장 미검증 |
| P3 넓은 후보 비교 | 고전/프론티어/segmentation/graph/sequence pilot | 동일 dev set·예산·평가, 실패 포함 재현 가능한 receipt | 미실행 |
| P4 데이터 효율/제어 | JEPA/DINO·증류·diffusion·Jev/Laya 비교 | frozen split, downstream/E2E 이득 및 비용 평가 | 미실행 |
| P5 밀봉 평가 | 최종 checkpoint·holdout·CAD 사용자 평가 | 오류/품질/검수 시간/호환성 기준 사전 고정 및 충족 | 미실행 |
| P6 업무 적용 | 검수 UI·배치·배포·모니터링 | 실제 요청 흐름, 원본 보호·실패복구, 담당자 사용 검수 | 미실행 |

## 첫 구현 세션의 구체 작업

1. 로컬 조사 기록과 워크 의뢰 연결 인덱스를 확인한다. 소량의 승인된 이미지–DWG를 읽기 전용으로 감사한다.
   주력 풀은 준공도면+변경전후.dwg가 함께 있는 의뢰로 제한하며, 실제 DWG의 변경전 영역과 치수/블록 dependencies를 검수한다. 썸네일 빨간 박스는 대상 설명으로만 사용한다.
   직원 확정 segmentation과 사내 CAD 페어의 교집합·canonical 정합·단위·변경상태를 검수하며, metric geometry와 semantic label을 별도 감독 축으로 연결한다. [사내 자산 재조사](research/2026-10-13-domain-reassessment.md)를 현재 적용 전략으로 따른다.
2. 우선 30~50개 페어 검수를 계획하고 도면 형태별 층화한다. 이는 목표 표본수이며 확보 수가 아니다. GT가 변경후인데 입력이 변경전이면 제외하거나 별도 과제로 격리한다.
3. 파일/hash/정합/단위/외부참조/버전/권리 문제를 보고하고 dataset v0.1 manifest를 고정한다.
4. CAD writer를 모델과 독립적으로 검증한다. target CAD·DWG 버전과 CAD 수정 성공의 검사 항목을 확정한다.
5. 동일 pilot split에서 고전 기준선·프론티어 VLM·Raster2Seq를 먼저 비교한다. 다른 후보도 준비가 되면 실행하며 후보를 단지 유행이나 이름 때문에 삭제하지 않는다.

## 자원·중단 규칙

첫 pilot 전에 run별 GPU 시간·API 토큰·재시도·총예산 상한을 기록한다. 현재 유료 실행 예산은 미설정이며 작업을 예약해두지 않았다. 데이터 정합 실패면 모델 튜닝 대신 페어 복구를 다음 실험으로 삼는다. 기준선 대비 이득이 없는 후보도 실패 원인·재시도 조건을 남기고 범위를 축소한다. 테스트셋에 반복 적응하는 실험은 중단한다.

# 평가 프로토콜 초안 v0.1

첫 baseline 전 dataset/split 및 metric 구현 revision, 좌표 tolerance, 목표 CAD·DWG version, 예산과 pass criteria를 고정한다. 현재 수치 목표는 미설정이며 성능 측정은 없다.

왜곡된 이미지 위 mask 일치와 canonical CAD metric geometry 정확도를 별도 측정한다. 벽 폭·길이·벽간 간격·dimension residual·opening host의 실물 오차와 원본 재투영 오차를 모두 보고한다. metric anchor 보유/unknown/충돌, perspective/종이 휨/비등방 resize, synthetic/실제 도메인을 분리한다. dewarp·dimension association·solver 효과는 ablation한다. 비내력 GT coverage가 없으면 0점이 아니라 측정 불가다.

| 축 | 측정 후보 | 필수 조건 |
| --- | --- | --- |
| 데이터 | 페어 승인율·정합 오차·제외 사유 | 검수 표본과 전체 분모, 정합 threshold 명시 |
| 기하 | corner/edge/room/door/window P/R/F1, 대칭 선 거리, 폭·치수 오차 | matching 방식·거리·각도 tolerance·단위 고정 |
| 위상 | 닫힘·자기교차·방 adjacency·개구부 연결·host 유효율 | 유효 사례만 골라 분모를 축소하지 않음 |
| 시각 일치 | render-back structural IoU/edge distance | 동일 정합 transform·해상도·lineweight·layer visibility |
| CAD | 변환/열기/수정/저장/재열기율, entity·layer 보존 | 실제 앱·엔진·버전과 로그·hash |
| 사용성 | 오류당 수정 종류·검수/수정 시간·재작성 대비 이득 | 동일 평가자 기준, 표본·측정 방식 |
| 효율 | E2E p50/p95·GPU/CPU 메모리·총비용 | OCR·routing·전후처리·변환·재시도·cold start 포함 |
| System-1 | accuracy/F1·Brier·ECE·risk–coverage·잘못된 자동통과율 | 한국어, option 순서/수/누락/왜곡 robustness, heldout 보정 |

scale unknown 사례는 실물 mm 오차 평가에서 제외 사유를 표기하고 정규화 기하/픽셀 지표와 함께 별도 집계한다. 원본의 문자·치수·틀 때문에 전체 pixel IoU가 구조 품질을 가릴 수 있으므로 구조 layer 지표를 분리한다. 판독 불가능 입력은 보류·사람 검수 대상으로 평가하며 hallucinated geometry를 성공 처리하지 않는다.

반복 controller는 candidate recall·action 선택·연속 좌표 parameter error·잘못된 tool/중복 action·종료/보류·누적 오류와 long-horizon 성공을 측정한다. 시각 모듈·렌더·solver·export·retry 비용까지 포함한다. 순수 자동과 HITL 허용량별 완료율·수정시간·intervention 수·잠금 위반·재작업을 분리한다. 최종 DWG에서 파생한 합성 action 이력을 실제 사람 작업 순서로 평가하지 않는다.

동일 pilot 입력에서 rule/기하, frontier, segmentation, graph, sequence, hybrid를 비교한다. backbone만 바꿀 때 decoder/writer/postprocess를 고정하고, 후처리 효과는 on/off ablation한다. 모델+writer 전체 개선과 모델 자체 개선을 구분한다.

기본 비교는 건물/평면 그룹 단위 bootstrap 신뢰구간 또는 paired 실패 표를 사용한다. 소표본 결과는 탐색으로 표시한다. 공개 논문의 room F1/IoU를 사내 DWG 성능과 직접 비교하지 않는다. 프롬프트·token budget·reasoning effort·SDK/model snapshot·retry policy를 고정하고 quota 실패를 기록한다.

최종 후보 선정 전 sealed test 평가 시점과 한도를 정한다. 실패·누락을 포함한 전체 결과 CSV/JSON과 CAD roundtrip, source/output hash가 있어야 성공으로 보고한다.

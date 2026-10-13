# 데이터셋 v0.2 확장 완료 · 2026-10-13 KST

사용자 확정에 따라 같은 의뢰 폴더의 준공도면과 변경전후.dwg를 현장의 input/output 페어로 취급했다. 별도 구조/특징점 정합 또는 사람 페어 승인으로 수집을 막지 않았다. 파일 무결성·변경전 추출·native CAD 전처리를 수행했다. 모델 학습은 실행하지 않았다.

## 실제 결과

| 항목 | 실측 |
| --- | ---: |
| 운영 연결 인덱스 / immediate-child 조회 | 8,764 / 2,912 |
| 후보·수집·ODA 읽기 변환·native 전처리 | 각 1,400 |
| 수집 원본 파일 / source bytes | 2,802 / 4,383,057,336 |
| 최종 릴리스 페어 | **1,383** |
| 영역 추출 불확실, 별도 보존 | 17 |
| 릴리스 원본 파일 | 2,768 |
| 변경전 DIMENSION 보존 | **32,413** |
| native block instance / text / mline | 2,145 / 29,039 / 1,409 |
| tar.gz shard / archive bytes | 22 / 4,719,688,444 |
| 원격 파일 / total bytes | 28 / 4,723,336,080 |
| 원격 readback primary artifact 검증 | **5,532개 일치** |
| exact pair 중복 / known exact identity split 누수 | 0 / 0 |

원본 SHA-256·size·mtime 전후 동일을 수집 시점에 확인했다. 원본과 다른 저장소에 저장/덮어쓰기/clean을 하지 않았다. 최종 target의 INSUNITS는 모두 4(mm)이며 원본 CAD→crop의 치수 측정점/값/effective style 보존을 검사했다. 이는 준공도면 숫자 판독·실물 정밀도 또는 실제 CAD 사용자 편집 성공 측정은 아니다. DIMENSION 없는 사례 1개는 no-dimensions 상태로 보존했다.

## 보관과 사용

사용자 요청으로 새 비공개 `youjunhyeok/img2dwg` HF 버킷을 만들고 `datasets/v0.2-2026-10-13`에 저장했다. source.dwg, full-resolution reference, before.dxf, native-components.json.gz와 preview가 shard에 있다. records.jsonl은 sample/shard/path/hash·crop·단위·split을, provenance.jsonl은 source hash/size/mtime를 연결한다. 실제 공유 경로·고객/의뢰번호는 local provenance에만 두며 원본 도면 내용은 승인된 비공개 버킷에 보관한다.

원격 목록/bytes를 대조하고 전체 22개 shard를 다시 다운로드해 SHA-256과 case membership, 각 primary 이미지/DWG/DXF/native component 해시를 검증했다. [비식별 집계](assets/2026-10-13-dataset-v02-summary.json), 비공개 run의 report·manifest·remote-readback receipt가 증거다. [재실행 안내](../harness/dataset-release.md)를 따른다.

## 분할과 전처리 경계

Exact image/DWG identity와 translation/회전/반전 동등 LINE fingerprint로 1,258개 union group을 만들었다. train 1,028 / validation 128 / calibration 77 / test 150이며 known exact identity 누수는 0이다. near layout-family grouping과 과거 학습 노출 검토는 다음 단계로 남아 현재 split을 밀봉 평가 정본으로 주장하지 않는다.

Native BLOCK/INSERT·DIMENSION·text·MLINE과 raw geometry/tag/스타일·DIMASSOC 정보를 유지했다. 업무상 벽/문/창/공간 조립과 DIMASSOC target 유효성은 후속 자동 전처리다. 원시 layer/type partition과 미해석 객체를 확정 semantic label이나 negative로 쓰지 않는다. 페어 관계와 label coverage는 별도 상태다.

## 실패·수정·다음 작업

처음 200개 중 199개가 omitted style default와 explicit default/숫자 타입 차이로 치수 변화 오탐을 냈다. effective default를 동일하게 비교하고 실제 배율 변경·치수 누락 검출을 유지했다. 초기 실패 기록을 보존했다. 장기 worker 메모리 누적으로 중간 실행을 중단하고 해시가 확인된 checkpoint를 재사용했다. scoped bbox memoization의 실제 crop/치수/entity/fingerprint 동등성을 확인했고 100개마다 worker를 교체해 최종 1,400개 전처리를 성공했다. protocol별 코드 hash/count를 집계에 남겼다. 관련 테스트 15개 pass.

다음은 이 버킷의 데이터를 이용한 업무 컴포넌트 catalog/factory·관계 전처리와 5개 debug 재구성, 이후 DINOv3 component/parameter/relation head smoke다. 이번 활동은 데이터 준비/실행기 검증이며 모델 성능·학습 성공으로 승격하지 않는다.

# 데이터 위치·페어·권리 계약

## 사내 입력

워크 의뢰의 연결 폴더 경로를 정본으로 사용한다. 기존 워크 문서·설정에서 UNC 기반 경로와 의뢰별 `smb_folder_path` 계약을 확인했다. 실제 루트·의뢰 인덱스·고객명은 `local/`과 `configs/paths.local.json`에만 기록한다.

전체 공유폴더 재귀 탐색은 기본 수집 방식으로 쓰지 않는다. 연결된 의뢰 목록을 입력으로 소량 감사부터 수행하며 서버 I/O를 제한한다. 링크 접근 실패는 누락으로 기록하고 연결되지 않은 로컬 대체 폴더를 자동 생성하지 않는다. 원본 읽기 권한과 결과 쓰기 권한은 분리한다.

## 페어 manifest 필수 필드

`sample_id`, 비공개 `case_id` 매핑, `building_group`, `layout_family`, 입력/GT SHA-256, 원본 수집시각, 이미지 크기·페이지·orientation, DWG header/version, 변경전/변경후, layout/modelspace/viewport, crop bbox, 외부 참조·폰트·block 의존성, 좌표변환·단위·scale 근거, 권리·외부처리 허용, 검수자/검수일/정합 상태, split, 제외 사유.

파일명이 같거나 같은 의뢰 폴더에 있다는 이유만으로 정답 페어로 확정하지 않는다. 렌더한 DWG와 입력 이미지의 점/선 정합을 측정하고 다른 평면·전후상태·부착 이미지·틀린 crop을 분류한다. 자동 정합 confidence와 사람 승인도 분리한다.

## split과 평가 오염 방지

- 같은 의뢰, 같은 건물, 동일 아파트 평면 계열, 시트 중복, scan/photo/render 및 augmentation은 하나의 그룹에 둔다.
- hash exact duplicate와 near duplicate를 검사한다. 서로 다른 case ID라도 동일 평면이면 그룹을 합친다.
- train/dev/calibration/test를 구분한다. routing threshold 및 보정은 calibration, 후보 선택은 dev, 최종 검증은 sealed test에서 수행한다.
- GT CAD 렌더 합성 이미지는 train group에서만 파생한다. 테스트 DWG를 합성 학습 데이터로 재사용하지 않는다.
- 사전학습 모델의 공개 데이터 오염 가능성을 기록하고 사내 holdout을 별도로 보고한다.

## 공개 후보와 사용 경계

[조사 보고서](research/2026-10-13-survey.md)의 공개 데이터는 사전학습·외부 일반화·geometry 검증 후보다. 공개 다운로드와 상용 이용허락은 다르다. 코드/annotation/원본 도면/가중치의 권리를 각각 확인하고 재배포하지 않는다. 외부 모델 API로 사내 도면을 전송하려면 사내 데이터 처리 허용 조건이 충족돼야 한다.

## 보존

원본은 수정하지 않는다. 학습 snapshot·run 결과·민감 manifest는 Git 외부의 접근 통제 저장소에 보관하고 SHA-256/receipt로 연결한다. 공개 실험 문서는 비식별 ID와 집계만 포함한다. 검수용 이미지도 공개 예외를 별도 검토하기 전에는 Git에 추가하지 않는다.

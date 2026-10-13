# 데이터 위치·페어·권리 계약

## 사내 입력

사용자 확정 주력 페어는 **같은 의뢰 폴더에 `준공도면`과 `변경전후.dwg`가 모두 있는 경우**다. DWG 내 변경전 평면 영역을 검수해 target으로 사용하며 변경후와 도곽을 섞지 않는다. thumbnail은 영역 설명용이고 CAD GT가 아니다. 기존 허용 4종 reference stem과 전체 페어 수는 새 주력 풀의 확정량으로 승계하지 않는다. 세부 계약은 [변경전 페어 설계](research/2026-10-13-closed-loop-hitl-design.md)에 있다.

워크 의뢰의 연결 폴더 경로를 정본으로 사용한다. 기존 워크 문서·설정에서 UNC 기반 경로와 의뢰별 `smb_folder_path` 계약을 확인했다. 실제 루트·의뢰 인덱스·고객명은 `local/`과 `configs/paths.local.json`에만 기록한다.

전체 공유폴더 재귀 탐색은 기본 수집 방식으로 쓰지 않는다. 연결된 의뢰 목록을 입력으로 소량 감사부터 수행하며 서버 I/O를 제한한다. 링크 접근 실패는 누락으로 기록하고 연결되지 않은 로컬 대체 폴더를 자동 생성하지 않는다. 원본 읽기 권한과 결과 쓰기 권한은 분리한다.

## 페어 manifest 필수 필드

`sample_id`, 비공개 `case_id` 매핑, `building_group`, `layout_family`, 입력/GT SHA-256, 원본 수집시각, 이미지 크기·페이지·orientation, DWG header/version, 변경전/변경후, layout/modelspace/viewport, crop bbox, 외부 참조·폰트·block 의존성, 좌표변환·단위·scale 근거, 권리·외부처리 허용, 검수자/검수일/정합 상태, split, 제외 사유.

2026-10-13 사용자 확정에 따라 같은 의뢰 연결 폴더의 준공도면+변경전후.dwg는 동일 현장의 input/output 페어로 취급한다. 별도 구조 정합 승인 없이 수집/전처리한다. 파일 무결성·변경전 crop·단위·컴포넌트 표현의 처리 상태는 페어 관계와 별도 기록한다.

## 사내 자산 연결 계약 (2026-10-13 추가)

직원 확정 segmentation 스냅샷과 기존 이미지–DWG manifest는 서로 다른 자산이다. 두 집합의 도면 교집합·정합을 먼저 검수하며 같은 sample이라고 가정하지 않는다. confirmed pixel semantics, canonical CAD geometry, 관측 왜곡/좌표변환을 각각 supervision 축으로 유지한다. geometry·host·dimension annotation이 없는 항목은 unknown/masked loss로 처리하고 negative로 만들지 않는다.

`wall_nonbearing`은 직원 확정 비내력, `wall_other`는 미확정이며 generic wall·해치·레이어 이름만으로 승격하지 않는다. CAD 정답에는 unit/scale, 벽 폭·길이·간격, opening host, dimension text↔측정점, shared endpoint/adjacency와 검수 상태가 필요하다. 기존 polygon editor의 reviewed 상태가 CAD metric geometry 승인까지 뜻하지 않는다. 근거·현황은 [재조사 보고서](research/2026-10-13-domain-reassessment.md)에 있다.

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

## 전유부·방향·치수 검수 확장

manifest에 입력 ROI/CAD target 경계, 포함/제외/미확정 영역, 이미지↔학습 target의 방향/좌표 정규화 근거·검수자(실제 집 방향 추론은 복원 선행 조건 아님), 치수 원장 revision/hash를 추가한다. 도곽 crop과 전유부 선택은 다르다. 옆집/공용부를 미라벨 배경 정답으로 만들지 않으며 치수 체인은 ROI 밖까지 관계를 검토한다. 같은 평면의 반전 사례도 같은 split 그룹이다. [최신 계획](research/2026-10-13-vector-first-training-plan.md)을 따른다.

## 컴포넌트 학습 정답

component ID/type·parameter·native members·instance transform·style·host/space/dimension 관계와 검수 상태를 기록한다. dimension picture의 LINE/문자를 독립 정답으로 중복 집계하지 않는다. GROUP/BLOCK으로 묶이지 않은 도형도 검수 grouping 후보로 유지한다. 원본 handle은 provenance이며 학습 class/저장 순서 정답이 아니다. [CAD 구조 감사](research/2026-10-13-component-supervision-audit.md)를 따른다.

## 확장 릴리스

최소 1,000개 실제 의뢰 페어를 새 비공개 Hugging Face img2dwg 버킷으로 준비한다. 원본 read-only, full-resolution reference, original DWG/before DXF/native component IR, hash·split·shard·remote readback 계약은 [릴리스 실행 안내](harness/dataset-release.md)를 따른다. 사용자 승인은 버킷 데이터 준비에 적용되며 모델 학습/외부 API 호출은 별도 범위다.

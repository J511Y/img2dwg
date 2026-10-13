# EXP-043 · 1차 CAD 합성 벡터 모델 및 비공개 inference Space

**후속 판정:** 실제 준공도면 복원에 실패하여 모델 기본 사용을 중단했다.
[EXP-044](2026-10-13-EXP-044-real-scan-failure.md)가 제품/배포 상태의 정본이다.
아래의 실행·합성 지표·파일 검증은 당시 기록이며 실제 복원 성공을 의미하지 않는다.

- 작성: 2026-10-13 KST, 당일 실행 기록. 실행·기록: Codex. 검토자 확인 필요. 연구 분류: R&D 후보.
- 학습 실행: 완료. 최종 목표인 치수 완전 DWG 복원: 미완료.
- 질문: native CAD 컴포넌트/좌표 감독으로 image→editable vector의 첫 baseline을 만들 수 있는가?
- 데이터: v0.2 private release 1,383개 중 train/validation 1156개 CAD 합성.
  train 1028, validation 128. calibration/test 미사용.
  exact source/dihedral identity split, near-family 검수 미완료. 독립 최종 성능으로 쓰지 않는다.
- 모델: DINOv3 ViT-B/16 frozen, revision `5931719e67bbdb9737e363e781fb0c67687896bc`.
  위치당 4-slot component center/6-coordinate/레이어 역할 후보 회귀. augmentation 후
  endpoint 순서를 정규화한다. native DIMENSION과 INSERT
  envelope를 LINE picture와 구분한다. 검수된 문/벽/공간 의미와 host association은 미학습.
- 입력: 768px, seed 20261013, 회전/반전의 image/GT 동시변환, 저해상도·blur·contrast/noise.
  perspective/종이 휨 복원과 실제 준공도면 coordinate fine-tune은 이번 run에 포함하지 않았다.
- 실행: tiny 100 steps 이후 full 2500 steps, A100/BF16, batch 4, AdamW 3e-4.
  full elapsed 1602.9초. 각 job timeout 90분, 공시 단가 $2.50/h 기준
  한 job의 상한 $3.75. 정확한 청구 금액은 확인 필요.
- 실패: 첫 FP16 job은 optimizer 첫 update 전 gradient overflow로 실패. 실패 로그/partial
  checkpoint를 attempt-01에 보존하고 BF16 attempt-02로 수정했다. attempt-02 single-slot은
  center 충돌과 augmentation endpoint 순서의 불일치가 발견되어 비교 baseline으로 보존했다.
  선택 모델은 attempt-03으로 border 후보 제거/등방 compact와 4-slot/endpoint 정규화를 적용했다.
  변경이 함께 들어갔으므로 하나의 수정 효과를 분리 주장하지 않는다.

## 작성기와 정답 범위

5개 factory에서 지원되는 native dimension 148개,
active block 26개를 재생성·재열기했다.
최대 치수 measurement 차이는 8.36735125631e-11 mm,
audit error 0. 이는 지원/viewport/최소 2px 조건을 통과한 GT에 대한 검사다. 원본 전체 치수의
완전성, native text/style/fixture semantic 동등성, 실제 CAD UI 편집을 증명하지 않는다.

이 5개 작성기 결과를 ODA 27.1.0으로 DXF→AC1032 DWG→DXF 재열기했다.
DIMENSION 148개, INSERT
26개와 mm 단위를 보존했다. 최대 measurement
변화 9.09494701773e-12 mm. GT factory의 로컬 변환
검사이며 Space의 DWG 다운로드나 실제 CAD UI 편집을 증명하지 않는다.

학습 정답 center 587,305개를 담았고 동일 cell 충돌
3,248개는 감독에서 빠졌다. 완전성 제한이며 confidence로
통과시킬 수 없다. 모든 선을 복원하는 decoder로 주장하지 않는다.

## 합성 validation 결과

평가 64개, threshold 0.25, unordered component Hungarian
one-to-one, endpoint 평균/arc midpoint/dimension label point 최대 오차 ≤8px.
mm 잔차·숫자 인식/누락·wall topology 성능은 이 metric에 포함하지 않는다.
표는 훈련 archive의 decoder snapshot에서 나온 값이다. 배포에서 graph node 탐색을
spatial bin으로 빠르게 하고, 같은 endpoint의 ARC 중간점/치수 배치가 다르면 별개로
유지하도록 보완했다. 서비스 배포 후의 곡선·치수 수치를 이 표로 대신 주장하지 않는다.

| type | prediction | target | match | precision | recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| segment | 32399 | 34364 | 13233 | 0.4084 | 0.3851 | 0.3964 |
| arc | 852 | 871 | 88 | 0.1033 | 0.1010 | 0.1021 |
| dimension | 1157 | 1437 | 21 | 0.0182 | 0.0146 | 0.0162 |
| symbol | 41 | 153 | 0 | 0.0000 | 0.0000 | 0.0000 |

훈련 loss 시작 14.471629, 마지막 100-step 평균 0.626583는
학습 진단이며 복원 성능으로 쓰지 않는다. 실제 준공도면 정확도는 수치로 검증하지 않았다.

## 서비스와 결과 계약

[비공개 Space](https://huggingface.co/spaces/youjunhyeok/img2dwg) · model revision `e00f601e871db6cdaa401c2910fa0741c61616e7`,
checkpoint SHA256 `0a5999ded25d4925417d9a07dee25c723deb94f8904fd3d3f1fdd6bd1ffdf072`. Space code revision `5b5b4a26a5a3a142bbf9e159fdca61d32fcbb851`.
모델은 별도 private repo, 자료는 private bucket. inference에 원본 CAD/데이터셋 접근 없음.
업로드→crop→벡터 preview→SVG/DXF/JSON/receipt download. SVG 안에는 raster image가 없다.
zoom/pan을 제공한다. DXF 객체를 재열어 audit한다. 서비스 형식 DWG 직접 생성은 미제공.

실제 인증 업로드 검증 3건. 각 SVG raster embed 0, DXF audit error 0,
checkpoint SHA 전파 일치. 실사진 전체 입력은 사람 전유부 crop 없이 API smoke로 실행했다.
이 검사는 artifact/인터페이스 계약이며 구조/전유부/수치 치수 정확성 검증이 아니다.
치수 후보 숫자는 `?`, 축척 미확정이면 unitless. 전체 ROI 폭의 확인된 사람 anchor만 mm 적용.

## 판단과 다음 실험

첫 학습/실시간 벡터 출력을 연결했다. 완성 CAD로 쓸 품질과 치수 완전성은 미확인/미달 상태다.
다음은 동일 검증 split에서 multi-slot/set decoder로 center 충돌 제거, CAD→실제 입력의
domain gap 검수/학습, dimension 숫자 OCR·측정점 association·constraint solver, 확정 업무
컴포넌트/host 관계, DWG converter/CAD UI roundtrip이다. 모델 용량만 키우거나 loss 감소만으로
진행을 평가하지 않는다. 전체 특징점 정합과 실제 좌우반전 판별을 선행 gate로 재개하지 않는다.

## 증거

실행 하네스: [vector-training](../harness/vector-training.md). private run root는
`configs/paths.local.json`의 `private_first_training_run`에서 찾는다. code/훈련 archive hash,
manifest, train.jsonl, evaluation.json, 실패 logs, gradient smoke, factory artifacts,
model receipt와 Space upload receipt를 보존한다. 원본 도면/개별 customer ID는 공개하지 않는다.
연구노트 증거 번들·실행 notebook은 private run 내에서 해시 검증한다. 검토자 확인 필요.

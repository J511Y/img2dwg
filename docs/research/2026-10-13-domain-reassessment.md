# 사내 자산 기반 이미지→정밀 CAD 복원 재조사 보고서

작성일: 2026-10-13 KST. 범위: 사용자가 추가한 Jippin 맥락, 사내 모델·라벨 매니저·학습 데이터·HF 배포 설정, 기존 이미지–DWG/CAD-IR 자산을 읽기 전용으로 조사했다. 새 학습·추론·변환 실험은 수행하지 않았다.

이 보고서는 [초기 조사](2026-10-13-survey.md)의 프로젝트 적용 판단을 보완한다. 초기 보고서는 공개 후보 목록으로 유지하며, **현재 데이터·학습·평가 전략은 본 보고서**를 우선한다. 코드 위치는 저장소명+상대 경로로 표기하고 실제 공유경로·고객·작업자 이름은 공개하지 않는다. 조사 원자료의 집계·SHA-256은 [감사 요약](assets/2026-10-13-domain-audit.json), 비공개 receipt는 Git 제외된 `local/reinvestigation-2026-10-13/`에 있다.

## 1. 결론과 목표 정정

당사는 이미 Jippin에서 **원본 도면 위의 벽체 객체 인식·선택·사전검토**를 개발했고, 이를 위한 직원 검수 라벨과 HF 학습·배포 경험도 보유한다. img2dwg의 핵심은 이 polygon을 그대로 추적하는 것이 아니라 **왜곡된 관측 이미지에서 치수·간격·연결 관계가 일관된 CAD 좌표의 벡터 그래프를 복원하는 것**이다.

공개 floorplan 데이터나 완성 모델을 그대로 가져오는 전략은 부족하다. 사내 CAD를 geometry 정답으로, 직원 확정 라벨을 wall semantics 정답으로 삼아 대응 관계를 검수하고 **사내 데이터로 복원 decoder/association head와 필요한 backbone을 학습**하는 경로가 주력 후보다. 공개 데이터는 모듈별 사전학습·외부 비교에 제한적으로 쓰며, 비내력벽 정답을 대신한다고 가정하지 않는다.

다만 사내 데이터로 학습해야 한다는 사실이 모든 weight를 무작위 초기화해야 한다는 뜻은 아니다. pretrained encoder+새 CAD decoder, domain pretraining+fine-tuning, 완전 scratch를 동일 split/예산에서 비교한다. 현재 증거는 먼저 앞의 두 경로를 검증할 근거를 주며 완전 scratch의 필수성·예산·성공을 확정하지 않는다.

## 2. Jippin과 img2dwg의 요구사항 차이

| 항목 | Jippin 기존 인식·사전검토 | img2dwg 정밀 CAD 복원 |
| --- | --- | --- |
| 출력 좌표 | 업로드 원본 픽셀 polygon/bbox | 왜곡을 제거한 canonical CAD 좌표 + 원본으로의 대응 변환 |
| 성공 기준 | 객체·속성·오버레이·선택과 후속 판단 | 엔티티 기하·위상·치수·간격·DWG 편집/저장 |
| 사진 왜곡 | 원본 위 오버레이는 관측 왜곡과 함께 정렬 | 원근·종이 휨·배율·비등방 resize를 보정하면서 원래 구조 복원 |
| 벽 라벨 | RC/직원 확정 비내력/미확정 구분 | geometry와 semantics를 분리해 벽 폭·연결·opening host까지 표현 |
| 정답 | 픽셀 mask/polygon + 직원 검수 attribute | 검수 CAD 엔티티·metric geometry·치수 association·제약 graph + semantics |
| 재사용 | 어휘, 검수 이력, high-res/tile, 학습/서빙 경험 | perception backbone/teacher와 label provenance로 활용 |
| 추가 연구 | 기존 segmentation metric | metric coordinate error, constraint conflict, topology, CAD roundtrip |

직접 확인한 `jippin/apps/api/src/agent/tools/segmentation.py::_parse_regions`는 polygon/bbox를 원본 픽셀로 유지한다. 같은 파일의 v4 매핑은 `wall_nonbearing → NON_LOAD_BEARING`, `wall_other/wall_unknown → UNKNOWN`이다. 오래된 v3 응답에 대한 호환 보정도 존재하므로 과거 응답의 class 문자열만 모아 학습하지 말고 vocab/source model version을 함께 확인해야 한다.

고객 벽체 선택→최종 사전검토 구현·운영은 사용자가 확인한 서비스 맥락이다. 이번 조사는 소비 코드와 배포 설정을 확인했으며 새 고객 세션을 만들어 E2E 동작을 재검증한 것은 아니다. img2dwg에서 벽 semantic을 보존할 수는 있어도 기존 철거 판정의 정답을 CAD geometry만으로 만들지는 않는다.

## 3. HF 학습·운영 자산의 실제 상태

2026-10-13 인증된 HF CLI로 endpoint 목록·상세와 최근 12개 job 기록을 읽었다. 현재 endpoint의 model repository는 `youjunhyeok/floorplan-mask2former-r2a-scale-joint22`, revision은 `0d2400ee41b5c74823d1d75881130c2f9d32583e`다. T4 GPU, 최소 replica 0이며 조회 당시 `scaledToZero`였다. 설정된 운영 모델을 확인한 것이며 이번 조사에서 이미지 추론 요청을 보내거나 가용성·성능을 새로 측정하지 않았다.

기존 `floor-plan-model-train/README.md`와 `docs/30_실험_기록/2026-09-22_R2a_운영_엔드포인트_교체.md`에는 원본 tile 1536/overlap 256, 19-class 계약, 실제 1/4 tile HTTP 추론과 Jippin parser 검증 기록이 있다. 기존 성공은 해당 날짜·조건의 기록으로 취급한다.

또한 `2026-09-30_벽체모델_최종보고.md`의 RF-DETR-Seg-XL G→A 후보는 운영 R2a와 별개다. 해당 보고서는 벽/비내력 인식 개선과 공간·비APT 회귀, parser replay 성공 및 HTTP endpoint 배포 미실행을 함께 기록한다. 따라서 “최신 후보=현재 운영 모델”로 단정할 수 없으며, 이 둘 모두 img2dwg의 CAD 정밀도를 검증한 모델은 아니다.

재사용할 항목은 HF job/run/checkpoint 기록, dataset lineage·hash, high-res inference·tile 병합 경험, confirmed semantics, model packaging이다. 모델의 geometry decoder·metric supervision과 CAD compiler는 별도 검증한다.

## 4. 사내 segmentation 데이터 직접 집계

아래는 **2026-10-13 로컬 파일을 실제 파싱한 수집 시점 스냅샷**이다. 현재 label manager 서버의 전체 최신량이나 서로 독립적인 사내 업무 페어 수를 뜻하지 않는다. 표의 image는 image record, annotation은 polygon record이며 augmentation/replay/동일 평면 중복 여부는 별도 감사 대상이다.

| 원자료 | 직접 집계 | 해석 |
| --- | --- | --- |
| `outputs/label_manager_confirmed/manifest.json` | STR 573 items, fetch status `saved` 573 | 직원 확정 자료를 가져온 스냅샷. 모든 이미지에 CAD 정답이 있다는 뜻은 아님 |
| `mask2former_str_spa_confirmed573v4_19c_original/dataset.json` | image 2,123, annotation 173,685, class 19 | confirmed source 573 + full replay source 1,550 |
| 위 dataset의 `wall_nonbearing` | annotation 27,407, 해당 image record 541 | train 21,857 / val 2,103 / test 3,447 annotation. 객체 수가 독립 도면 수를 뜻하지 않음 |
| `mask2former_r2a_canvas_20260921/dataset.json` | image 2,101, annotation 173,685 | confirmed 573 + replay 1,528. 같은 NB annotation 수를 가진 별도 preprocessing 표현 |

이 두 가공 manifest를 합쳐 도면·annotation 수를 늘려 계산하면 안 된다. 기존 모델 최신 후보의 A/G 풀은 또 다른 pixel-disjoint 학습 계약이며 위 historical manifest와 동일하지 않다. 최종 보고에 적힌 A train 1,617/val 188은 **기존 보고 기록**이고 이번 표의 직접 집계와 분리한다.

기존 개발 holdout44에는 `wall_nonbearing` GT가 없어 해당 class 측정이 불가능했다. 이는 확정 비내력 라벨이 사내 전체에 없다는 뜻이 아니라 **평가 세트별 coverage 문제**다. 복원 프로젝트도 geometry·NB semantics·dimension을 각각 평가할 수 있는 표본 coverage를 먼저 확보해야 한다.

## 5. AIHub의 괴리: 무엇이 부족했는가

### 5.1 의미 라벨의 차이

`floor-plan-model-train/src/floorplan_cv/aihub.py::WALL_ATTRIBUTE_SLUGS`는 `기타벽 → wall_other`, `비내력벽 → wall_nonbearing`을 분리한다. `기타벽`은 미확정이며 직원이 확정한 비내력과 같지 않다. 라벨 매니저 UI의 선택지도 `철근콘크리트벽/기타벽/비내력벽`이다.

따라서 AIHub의 wall/기타벽·공개 데이터의 generic wall·외관상 얇은 선을 비내력 정답으로 승격하면 감독이 틀어진다. 그림만으로 확인 불가한 벽은 unknown으로 두며, 직원 label provenance와 검수 기준을 유지한다. 역사적 문서 중 기타벽을 비내력으로 느슨하게 해석한 표현은 현재 코드의 분리 계약을 우선해 읽는다.

### 5.2 도면·해상도·객체 표현의 차이

기존 `2026-05-26_wall_other_door_라벨_노이즈_진단.md`에는 평면도 외 단면/입면 혼재, 작은 얇은 벽 라벨, 문 swing arc 불포함, annotation fragmentation 문제를 진단한 기록이 있다. 원본 tile·plan-only 필터·polygon 병합·arc 보강이 필요했던 이유다. 해당 역사적 비율을 오늘 전체 데이터의 재집계처럼 인용하지 않는다.

AIHub와 공개 corpus가 쓸모없다는 결론은 아니다. generic geometry/perception 감독은 사용할 수 있지만, **한국 단위세대의 직원 확정 wall semantics와 정밀 canonical CAD supervision을 충분히 제공한다고 확인되지 않았다**. 외부 dataset 전체에 비내력 라벨이 절대 없다고 주장하지 않고, 후보별 문서·schema에서 검증된 계약을 기록한다.

### 5.3 현재 label manager는 CAD 정답 도구가 아니다

`apps/label_manager_app.py::rebuild_annotations`는 polygon으로 bbox/area를 재계산하고 category/attributes/review 수정 이력을 유지한다. 웹 `src/lib/types.ts`도 segmentation·polygon·bbox·attributes 중심이다. 읽은 표준 구조에서는 CAD 단위·벽 중심선/폭·opening host·dimension association·constraint graph를 확정하는 명시적 계약을 확인하지 못했다. 확장 metadata가 가능한 구조라는 점과 현재 표준 감독 계약을 구분한다.

기존 검수 도구는 **semantic 라벨과 이력을 재사용**하고, CAD 복원용 검수 화면/스키마를 추가하는 것이 합리적이다. 기존 운영 label manager를 이번 조사에서 변경하지 않았다.

## 6. 기존 이미지–DWG/CAD-IR 자산 재감사

`data-pipeline`에는 이미 다음 자산이 있다. 대부분 미커밋 작업 트리이므로 **현재 스냅샷의 재사용 후보**다. 기존 보고 JSON을 읽은 것이며 원본 2,286개를 모두 열거나 새로 compiler를 실행하지 않았다.

| 자산·원자료 | 확인한 내용 | 적용 한계 |
| --- | --- | --- |
| `data/floorplan-model/dataset_manifest.json` | records 2,286, declared missing 0; 기존 split train 1,817/val 218/test 251 | usable aligned gold 2,286개가 아님. 변경상태·동일 평면·좌표 정합 승인 필요 |
| `reports/floorplan_cad_reconstruction/summary.json` | hard label alignment와 model training이 정합 검수 전 `no_go` | 정합 문제를 이미 인지. 데이터 존재만으로 학습 준비 완료라고 할 수 없음 |
| `cad_ir_smoke_eval.json` | 기록 50, CAD-IR success 50 | 기존 export smoke 결과. 이미지→벡터 모델의 성공률 아님 |
| `roundtrip_eval.json` | 기록 20, compile/render 각 20 | 지원되는 core entity의 기존 DXF/render smoke. 실제 CAD 사용자 수정/저장·DWG 완료 증거와 다름 |
| 같은 roundtrip report | DIMENSION 476, HATCH 330, INSERT 24 등 skipped; duplicate entity 1,536 보고 | supported entity 보존율 1.0을 전체 CAD 완전성으로 해석하면 안 됨 |
| `dimension_fix_aggregate.json` | repaired ID 2,286·missing/index gap 0 기록; validation 11개 parse·dimension positive 11 | DWG crop repair 보고. canonical 정합·dimension association 정답은 별도 |
| `data/floorplan-cad-entity-v1/dataset_meta.json` | line/polyline/arc/text_box/dimension/symbol/hatch와 7개 semantic, image size 512 | 기존 smoke target. 비내력 구분과 정밀도 평가 계약으로 그대로 채택 불가 |

기존 `prepare_manifest.py::assign_split`는 record ID hash로 split을 정한다. 건물·동일 평면 계열 grouping을 보장하는 코드가 아니므로 현재 정책으로 다시 감사해야 한다. 새 split을 만들면 옛 test를 보지 않았다고 자동 주장하지 말고 과거 노출 이력도 기록한다.

DWG에서 엔티티·레이어·DIMENSION을 추출하는 기존 기반은 가치가 크다. 그러나 레이어 이름이나 hatch만으로 비내력 의미를 확정하지 않는다. dimension 숫자는 표시 override·units·실제 측정 geometry·연관점까지 확인해야 한다. source crop이 변경전/변경후 중 어느 상태인지도 geometry supervision에 포함한다.

## 7. 필요한 정답 데이터: 세 축을 연결해야 한다

| 감독 축 | 기존 자산 | 추가해야 할 계약 |
| --- | --- | --- |
| 관측 이미지/왜곡 | 실제 사진·스캔, high-res/dirty augmentation 경험 | 원본 페이지/crop, perspective·nonrigid warp, 합성 forward/inverse map, 실제 정합 승인 |
| canonical geometry | 사내 DWG·raw CAD-IR | mm 또는 검증된 단위, 원점·축, line/arc·폭·길이·간격·host·폐합/adjacency graph |
| 의미·근거 | 직원 확정 RC/NB/unknown 라벨과 review metadata | pixel region↔CAD wall 대응, canonical semantic, 불확실성·검수 근거·변경상태 |

이 세 축은 아직 하나의 완성된 gold dataset으로 연결됐다고 확인되지 않았다. AIHub confirmed573과 사내 DWG2286의 도면이 서로 대응한다고 가정하지 않고, 이미지 fingerprint/메타데이터 후보→사람 검수로 교집합을 먼저 측정한다.

완전 paired gold가 적을 때도 학습은 분리할 수 있다. CAD-only에서는 geometry/constraint supervision, confirmed pixel label에서는 semantic supervision, 둘이 연결된 샘플에서 joint supervision을 한다. 라벨 없는 항목에는 masked loss를 적용하고 absent annotation을 background/negative로 처리하지 않는다.

CAD→raster→synthetic distortion으로 알려진 정답을 만든 뒤 실제 사진/스캔 aligned gold로 fine-tune한다. split은 augmentation 전에 건물/평면 계열 단위로 고정한다. 실제 페어를 정합 confidence만으로 hard target에 넣지 말고 승인 상태에 따라 gold/silver/unreviewed/rejected를 분리한다. 모델 pseudo-label은 직원 확정과 별도 provenance로 유지한다.

### 검수 도구에 필요한 추가 화면

관측 이미지·canonical CAD render·재투영 overlay를 함께 보여주고, geometry와 의미를 별도 편집한다. 벽선/두께/간격·corner·door/window host·치수 텍스트↔측정점·arc를 선택·수정한다. 치수 anchor와 평행/직교/연속/동일 두께 제약의 근거·unknown을 기록하며, 검수 이력·동결 version·hash를 남긴다. 이는 **구현 제안**이며 현재 도구에 존재한다고 주장하지 않는다.

## 8. 왜곡 보정과 정확한 치수 복원 설계

평면 perspective는 homography 후보지만 종이 휨은 비선형 warp가 필요하며, 도면 자체의 왜곡/축척 문제까지 한 변환으로 해결되지는 않는다. 이미지 네 모서리를 펴는 것과 각 벽·문·창의 metric geometry 복원은 따로 검증한다.

알려진 치수·축척 anchor가 없으면 절대 mm를 유일하게 식별할 수 없다. 실제 수치 정확성이 목표인 만큼 scale unknown은 성공 결과와 분리하고 사람 입력 또는 추가 근거를 요구하는 상태로 둔다. 흔한 문 폭/벽 두께 같은 prior는 추정 근거이며 정답 anchor로 확정하지 않는다.

추천 출력은 wall/opening/room entity graph와 confidence, geometry transform, constraint/dimension association이다. solver는 관측 증거·명시 치수·parallel/perpendicular/shared endpoint·wall thickness·opening host를 최적화하며 충돌을 숨기지 않는다. 경사벽/곡선에 직교 제약을 강제하지 않고 anchor 부정확성·dimension OCR 오독은 outlier/검수로 분류한다. 표현 예시는 다음과 같다.

```text
weighted 관측 재투영 오차
 + 근거 있는 치수/간격/폭 잔차
 + 연결/폐합/host 관계 위반 비용
 → canonical CAD-IR + constraint conflicts + review flags
```

이는 제안 목적함수이며 loss weight·solver·미분 가능성·성능은 아직 정하지 않았다. constraint를 학습/추론 중 이용하는 것과 DWG 내부 parametric constraint entity로 저장하는 것도 별개다. 1차 목표는 정확한 편집 가능 geometry이며 native constraint export는 writer 지원·CAD 호환성 확인 후 별도 범위로 정한다.

문서 dewarping을 무조건 앞에 붙이지 않는다. 기존 DocRes 검토는 geometry 변화 우려를 남기고 복원 트랙을 동결했다. [UVDoc 공식 코드](https://github.com/tanguymagne/UVDoc)는 grid 기반 보정 후보지만 OCR용 flattening 품질이 mm 정확성을 보장하지 않는다. 학습된 dewarp·homography·직접 canonical decoder를 비교하고 실제 치수·간격·line deviation으로 판단한다.

## 9. 공개 데이터·모델의 역할 재배치

| 후보 | 프로젝트에서의 역할 | 채택 전 검사 |
| --- | --- | --- |
| CubiCasa5K/FloorPlanCAD/Structured3D/Raster2Graph/WAFFLE | generic perception·topology 사전학습·외부 OOD 비교 | NB semantic과 metric CAD pair를 대신하지 않음. 원 annotation/schema·권리 확인 |
| Raster2Seq/RoomFormer/HEAT/Raster-to-Graph | 사내 CAD GT로 retrain/decoder 구조 비교 | room polygon/graph→벽 폭·개구부·치수 확장, 원 입력 protocol와 domain gap |
| FloorplanVLM/프론티어 VLM | 구조 제안·OCR/association·teacher·repair baseline | 사내 aligned gold 평가, 좌표/숫자 환각·token 길이·총비용. generic model zero-shot 성공을 기대만으로 확정하지 않음 |
| 기존 R2a/RF-DETR 후보 | 원본 좌표 perception·semantic teacher·backbone | mask boundary를 canonical vector 정답으로 쓰지 않음. train/test 노출 이력 |
| DINO/JEPA/LeJEPA | 사내 unlabeled 도면 domain pretraining·encoder 비교 | 동일 CAD decoder downstream 기하·라벨 효율, SSL에도 test family 제외 |
| Jev/Laya | JSON 상태의 QC routing·재시도·검수 prioritization | 정밀 geometry/치수 generator가 아님. unknown·calibration·E2E 비용 검증 |
| [SketchGraphs](https://github.com/PrincetonLIPS/SketchGraphs) | primitive–constraint graph와 auto-constraint 학습 참고 | 기계 CAD sketch domain, 한국 주거 평면/NB 정답 아님. 데이터·code 권리 분리 |
| [DAVINCI](https://arxiv.org/abs/2410.22857) | constrained sketch inference·constraint-preserving augmentation 참고 | 이미지→평면도 metric 복원과 동일 과제 아님. 사내 구조로 재설계 필요 |

[Autodesk AutoConstrain 연구](https://www.research.autodesk.com/blog/using-ai-to-power-autoconstrain-in-fusion-automated-sketching/)는 geometry와 dimension constraint 예측을 학습 대상으로 삼는다. [AutoCAD dimensional constraints 문서](https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-24EC28C2-D67E-4160-819E-6735E9B9EDFC.htm)는 geometry를 제어하는 제약의 표현을 설명한다. 두 출처는 constraint 연구 방향의 근거이며 img2dwg에 바로 쓸 pretrained floorplan model이 있다는 증거는 아니다.

## 10. 학습 전략과 실험 순서

### 10.1 사내 학습의 세 대조군

1. **pretrained encoder + 새 structured decoder:** CAD entity set/graph·geometry·dimension association을 사내 데이터로 학습. 기존 segmentation head는 보조 감독 또는 teacher로 비교한다.
2. **사내 domain pretraining → supervised CAD:** train-family의 CAD 렌더/미라벨 이미지로 representation·geometry pretraining 후 aligned 실제 이미지와 semantics를 학습한다.
3. **완전 scratch:** 같은 규모/예산으로 random init 대조. 큰 frontier 모델 자체를 새로 사전학습하는 범위와 구분하며 pilot에서 label 효율·수렴·오류를 보고 확대 여부를 결정한다.

출력 표현은 entity set+association graph와 autoregressive sequence를 비교한다. 많은 unordered entity·긴 dimension/text와 incomplete labels의 차이를 평가한다. "기존 모델을 배포해 해결"에서 **사내 target 정의·label engine·decoder 학습이 중심**인 전략으로 옮긴다.

### 10.2 먼저 실행할 검증

| 순서 | 실험 | 통과/다음 판단 |
| --- | --- | --- |
| A | segmentation573↔CAD2286 교집합/정합·단위·전후상태 감사 | 실제 joint gold 수·class/치수 coverage, 불일치 유형 확인 |
| B | GT CAD-IR 정규화·DIMENSION/INSERT/HATCH·중복·host 감사 | 입력 CAD를 roundtrip해도 metric geometry가 보존되는지 확인 |
| C | CAD 렌더→알려진 warp→canonical geometry synthetic pilot | 관측/역변환·entity correspondence/loss 검사, 실제 일반화 별도 |
| D | rule+solver, segmentation+solver, pretrained structured decoder 비교 | 동일 real dev에서 mm/간격·위상·uncertainty와 총비용 |
| E | domain pretraining·sequence/VLM·scratch 대조 | label budget·실제 왜곡·class별 성능·constraint 충돌 ablation |
| F | 밀봉 실제 사진/스캔+CAD 사용 검수 | 성공 분모·보류·잘못된 치수/자동통과·수정시간 보고 |

초기 30~50개 paired gold를 층화 검수하는 계획을 세우되 수량·compute budget·정량 threshold는 실제 가용량을 본 뒤 고정한다. 후보 모두 시도할 수 있도록 백로그를 유지하지만 정합이 안 된 hard target으로 대규모 GPU 학습부터 시작하지 않는다.

## 11. 평가 변경: segmentation score로 정밀 CAD를 판정하지 않는다

canonical 좌표의 corner/line/arc error, 벽 폭·길이·벽간 간격, explicit dimension residual, opening 위치/폭/host, room 폐합·adjacency, 실제 CAD entity/layer 보존과 열기·수정·저장·재열기를 측정한다. 원본으로 재투영한 image consistency는 보조 축이다. mask IoU가 높아도 실제 치수가 틀리면 정밀 복원은 실패다.

실제 metric anchor 보유/unknown·충돌, clean scan/평면 perspective/종이 휨/비등방 resize, 경사·곡선·얇은 선·부분 가림을 분리한다. generic image overlap과 topology correctness, NB semantic accuracy, CAD unit 정확도를 따로 보고한다. GT coverage 없는 class는 0이 아닌 측정 불가다.

학습 dewarp vs no-dewarp, image-only vs dimension-assisted, solver on/off, generic vs confirmed semantics, synthetic-only vs real fine-tune, pretrained vs scratch를 대조한다. 상대 오차·mm threshold는 쓰는 CAD 작업의 요구 정밀도와 anchor 신뢰도를 확인해 사전에 고정한다.

## 12. 출처·증거 경계와 다음 결정

사내 코드·JSON 증거 목록과 hash는 [감사 요약](assets/2026-10-13-domain-audit.json)에 있다. 소스 Git HEAD·관련 dirty 여부를 함께 기록했으며 기존 저장소를 수정·clean·stage·commit·deploy하지 않았다. private HF endpoint 설정/원본 경로는 비공개 receipt로 분리했다.

이번 결과는 **연구 준비·자산 재조사**다. 직접 집계와 기존 실험 보고를 구분하며 모델·writer 성능의 새 실측은 없다. 다음 결정에 필요한 것은 usable aligned joint gold 수, 목표 CAD 정밀도·단위, dimension/host/semantics 정답 계약, 예산과 group split이다. 이를 확보하면 P1/P2를 통과하고 사내 데이터 중심 decoder 학습으로 진행할 수 있다.

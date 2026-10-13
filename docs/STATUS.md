# 현재 상태 · 2026-10-13 KST

## 최신 정정: 실제 스캔 복원 실패 · 모델 기본 사용 중단

사용자가 제공한 실제 입력 결과에서 거대한 원호/흩어진 선이 확인됐다.
첫 모델은 raw 준공도면 페어를 학습하지 않고 CAD 합성 렌더만 학습했다.
이미지상의 중심점과 canonical CAD 좌표를 같은 국소 회귀로 처리한 설계,
독립 endpoint/3점 ARC와 구조 제약 부재, 실제 시각 품질 없이 파일 생성만 검사한
출시 판단이 실패했다. 아래의 학습/서빙 성공은 파일/실행 계약만이며 제품 성공이 아니다.

실패 모델을 Space 기본 출력에서 제외했다. 현재 출력은 명확하게 표시한
관측 선 검출 기준선으로, 학습된 CAD 복원/중심선/치수/컴포넌트 출력이 아니다.
첨부 사례는 원본 해상도가 없는 screenshot crop으로 실패 재현했다.
[EXP-044](experiments/2026-10-13-EXP-044-real-scan-failure.md)를 정본으로 읽는다.

다음: 실제 준공도면→canonical CAD 컴포넌트 감독, 입력 픽셀의 국소 좌표 회귀와
canonical 출력 구분, 관계/제약·ARC parameterization, 실제 5개 train 재현과
20개 별도 validation 구조/치수 평가. 실제 도면 품질을 확인하기 전 모델을 기본 배포하지 않는다.

## 최신: 첫 학습·벡터 inference Space

사용자 승인으로 DINOv3 frozen + 4-slot component coordinate head를 학습하고 별도
[private Space](https://huggingface.co/spaces/youjunhyeok/img2dwg)에 배포했다.
CAD 합성 train 1,028/validation 128개, tiny 100/full 2,500 steps, A100/BF16.
합성 validation 64개 선분 F1 0.396, curve 0.102, dimension candidate 0.016.
이 수치는 raw 준공도면/mm/치수 숫자 성능이 아니다. near-family 검수도 미완료다.

첫 FP16 overflow 실패와 single-slot/endpoint 불일치 baseline을 보존하고 endpoint
정규화/4-slot/border 후보 제거·등방 compact로 보완했다. 현재 학습 정답 충돌 누락
3,248개는 별도 제한으로 기록한다. 모델 출력의 구조/치수 정밀도는 완료 기준에 미달한다.

Space는 crop, 벡터 확대/이동, SVG/DXF/좌표/receipt 다운로드를 제공한다. inference에
source CAD 접근이 없으며 SVG에는 raster embed가 없다. 치수 후보 `?`, 축척 미확정은
unitless다. 직접 DWG 다운로드와 실제 CAD UI 편집 검증은 미완료다.
5개 GT factory는 ODA DXF→DWG→DXF에서 DIMENSION 148/INSERT 26과 mm를 보존했다.
이는 모델 복원 정확성과 별도 검사다.

최신 [EXP-043](experiments/2026-10-13-EXP-043-vector-first.md),
[실행 하네스](harness/vector-training.md)를 읽는다. private run/model/deployment/실제
업로드 receipt는 local config에서 찾는다. 다음은 실제 domain fine-tune,
dimension text 위치 감독/OCR·association·solver와 native 업무 컴포넌트/host 관계다.

아래는 단계별 당시 기록이다. 초기 미실행 상태를 현재 학습 금지로 해석하지 않는다.

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

## 최신 실행 우선순위 수정

사용자 요청으로 전체 특징점 정합 재시도는 중단했고 기존 결과를 보존했다. 다대일 대응 방지 단위 테스트 9개는 통과했으나 실제 40개 재정합은 하지 않았다.

현재 정본은 [벡터 우선 학습 계획](research/2026-10-13-vector-first-training-plan.md)이다. 입력 방향의 전유부→치수에 맞는 DWG가 핵심이며 실제 좌우반전은 CAD/후속 기능으로 처리한다. 초기 전유부 선택은 수동 ROI를 허용한다.

다음 구현은 5개 CAD로 supervision/GT writer 확인 → DINOv3 freeze+graph decoder tiny 학습 → 합성 학습/Raster2Seq 비교 → 실제 표본 fine-tune → preview/HITL/새 DWG 생성이다. 합성 학습 준비와 실제 검수는 병행하며 전체 40개 승인 완료를 학습 개발 선행 조건으로 두지 않는다.

이번에는 공식 모델 metadata와 Raster2Seq 512 config를 확인했고 DINOv3 weight dry-run만 했다. 모델 weight 다운로드·추론·학습·GPU job·운영 변경은 미실행이다. decoder/치수 association/solver/UI는 계획 상태다. 이전 913개 보존 pass는 입력 치수 완전성/실제 길이 검증이 아니다.

## CAD 컴포넌트 구조 감사 완료

[40개 감사](research/2026-10-13-component-supervision-audit.md): 로컬 source/before/reopened 120개 읽기 전용 검사. 변경전 DIMENSION 913개, INSERT 76개(13개 파일), 명시 GROUP 0개 파일, DIMASSOC object 700개를 확인했다. 보유 block 정의와 현재 사용 인스턴스·분해된 도형을 구분했다. 120개 SHA/size/mtime 무변경, 신규 auditor 테스트 2개 pass. 실제 컴포넌트 의미 승인·DIMASSOC 관계 검증·factory/모델 학습은 미실행이다.

첫 학습 전 component catalog와 5개 factory/GT roundtrip을 수행한다. DINOv3 backbone 선택은 유지하며 출력부를 컴포넌트 type/parameter/관계와 내부 geometry로 구체화한다. 원본/기존 pilot receipt는 보존했다.

## 1,000개 이상 확장·원격 릴리스 완료

[데이터셋 v0.2](research/2026-10-13-dataset-v02-release.md): 1,400개 same-case 페어 수집/ODA/native 전처리 성공. 자동 변경전 조건을 충족한 1,383개를 새 비공개 HF img2dwg 버킷에 저장했다. 17개 영역 불확실은 별도 보존. DIMENSION 32,413개 crop 보존, source 무변경, exact pair/split identity 누수 0. 전체 22 shard 및 5,532 primary artifact 원격 readback 해시 일치. 테스트 15개 pass.

이 사용자 확정 페어 정책이 앞선 구조 정합/사람 페어 승인 수집 gate를 대체한다. 업무 semantic assembly와 DIMASSOC target 보강·near-family grouping은 다음 전처리 상태이며 모델 학습은 미실행이다. 실행 방법은 [릴리스 하네스](harness/dataset-release.md), private URI/run은 local config에서 찾는다.

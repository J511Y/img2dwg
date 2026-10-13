# EXP-044 · 실제 스캔 실패와 배포 판단 정정

- 날짜: 2026-10-13 KST, 기록: Codex, 검토자 확인 필요.
- 상태: 첫 coordinate 모델의 실제 복원 실패. 기본 서비스 사용 중단.
- 분류: R&D 후보의 부정 결과/실패 분석. 선 검출 기준선은 완성 모델 성과가 아니다.

## 확인된 문제

사용자 screenshot에는 도면에 없는 거대한 원호와 흩어진 선이 있다. 이를 품질이 낮은
정상 초안으로 해석하면 안 된다. 실제 입력의 구조를 복원하지 못한 실패다.

첫 1,028개 학습은 회사의 CAD를 렌더링한 합성 입력이다. 같은 의뢰의 **원본 준공도면
1,028장을 input으로 학습한 것은 아니다.** 실제 입력 업로드 검사는 SVG/DXF/해시/재열기
계약만 확인했고 실제 형태·중심선·치수·컴포넌트 복원은 평가하지 않았다.
합성 선분 F1 0.396도 실제 도면 변환을 제공할 근거가 부족했다. 배포 판단은 잘못됐다.

## 원인과 아직 확인되지 않은 부분

합성의 깨끗한 CAD 획과 실제 스캔의 종이/음영/폰트/해칭/왜곡/크기가 다르다.
dense center/endpoint head는 같은 plane의 합성 위치 감독에 묶였으며, 실제 raw 입력에서
canonical CAD graph를 생성하는 decoder로 검증되지 않았다. component/관계/치수 제약은
미구현인데 독립 geometry를 직접 그렸다. 3점 ARC의 triangle area가 작으면 circumcircle
radius가 매우 커진다. finite endpoint 검사만으로 이 곡선 전체의 유효성을 보증할 수 없다.

이 원인들의 개별 기여를 ablation으로 분리하지 않았다. 사용자 전유부 선택이나
좌우반전을 실패의 책임으로 돌리지 않는다. 전체 특징점 정합도 재개하지 않는다.

## 실행한 수정

첨부 screenshot에서 입력 사진 영역 389×517px을 추출해 같은 checkpoint로 실패를
재현했다. 원본 업로드 해상도가 없는 파생 입력이며 실제 원본 전체에 대한 정량 평가가 아니다.
관측 ink 거리/곡선 전체 범위 진단과 별도의 OpenCV LSD 선 검출 기준선을 비교했다.
기준선은 선분 829개를 검출했으며, 원래 평면 구조를 대략 유지한다. 도곽/문자/해칭,
끊긴 선·중복도 포함한다. 중심선·업무 컴포넌트·치수·canonical geometry 복원이 아니다.

Space 기본 출력에서 실패 모델을 제외하고, 현재 출력이 관측 선 기준선이라는 사실과
실패 상태를 화면/JSON/Space card에 표시했다. 기준선에는 ARC/DIMENSION을 임의 생성하지
않는다. screenshot-derived 실제 업로드, source marker, SVG/DXF와 재열기를 검사한다.
대형 원호/미지원 선·빈 입력/관측 선 검사 4개가 통과했다. 이 역시 모델 품질 검증은 아니다.

Private evidence: `outputs/vector-recovery-2026-10-13/`의 입력 crop, failure comparison,
assessment와 live baseline receipt. 고객 도면 파생 이미지를 공개 Git에 넣지 않는다.
checkpoint/첫 run/부정 결과는 삭제하지 않는다.

## 다음 학습의 계약

1. 실제 raw 준공도면–같은 의뢰 canonical CAD를 input/output으로 사용한다. native
   컴포넌트·기준점·치수값을 보존하며, 필요한 치수를 작은 pixel 길이라는 이유로 버리지 않는다.
2. 입력 pixel coordinate의 dense 회귀와 canonical output frame을 구분한다. component
   set/parameter/관계 decoder와 결정론적 writer, 안정된 ARC parameterization을 사용한다.
3. 실제 5개 training pair에서 구조 재현 가능성을 먼저 확인한다. tiny fit은 generalization
   증거가 아니다. 별도 실제 validation 20개에서 GT CAD 구조/geometry·치수 누락/값·레이어와
   시각 결과를 평가하고 기하 기준선과 구분한다. feature matching/사람 페어 승인 gate를 추가하지 않는다.
4. 이 결과를 통과하기 전 1,000개 확장 run이나 모델 기본 배포를 진행하지 않는다.
   선/문/벽이 제 위치에 있고 필요한 치수를 놓치지 않는지 먼저 판정한다.

새 raw-pair 학습과 decoder 구현은 아직 planned다. 관측 선 기준선으로 ML 복원 성공을
대신 주장하지 않는다. 중심선→치수 제약→세부 요소와 DWG/CAD 실제 검증의 원래 목표를 유지한다.

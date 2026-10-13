# CAD 출력 계약 초안 v0.1

현재 문서 계약이며 schema와 compiler 구현은 없다. 후보마다 내부 구조가 달라도 공통 CAD-IR로 변환해 동일 writer와 평가를 사용한다. 모델이 엔진마다 다른 출력 포맷을 만들어 비교를 흐리지 않도록 한다.

## 좌표와 의미

- 원본 픽셀·정규화 좌표·CAD 좌표를 구분하고 전방/역방향 변환, crop·회전·perspective transform을 기록한다.
- CAD 좌표는 2D 우수계, y축 방향/원점/단위를 명시한다. 초기 단위 후보는 mm이며 실물 기준점 확인 전 `scale_status=unknown`이다.
- 벽 중심선과 양면선·폭을 혼동하지 않는다. 방은 닫힌 경계와 semantic, 문·창은 host wall 및 offset/폭/방향을 가진다.
- 최소 엔티티 후보: LINE, LWPOLYLINE, ARC, CIRCLE, TEXT/MTEXT, DIMENSION, INSERT/BLOCK. 단계별 지원 범위를 명시한다. 미지원은 누락 보고에 남긴다.
- 엔티티 ID, layer, source evidence, confidence, uncertainty, 관계 그래프를 유지한다. 모든 선이 같은 layer인 결과를 semantic 복원 성공으로 취급하지 않는다.
- 이미지에서 보이지 않는 문·벽·치수를 설계 관행만으로 확정하지 않는다. 벽 법적/구조적 속성은 이 계약의 목표가 아니다.

## 필수 검증

finite 좌표, 최소 길이, 중복/겹침, 자기교차, 닫힘, host 관계, 문 opening 연결, 방 adjacency, text/font, block/xref 포함 상태, INSUNITS·extents·도면 version을 검사한다. tolerance는 픽셀/실물 단위를 분리한다. 임의 Manhattan snapping은 금지하고 dominant axis와 경사/곡선 증거를 보존한다.

## DWG 제공 경로

DXF 작성 후보는 ezdxf, DWG 변환 후보는 설치된 ODA File Converter 및 라이선스 확인 후 ODA SDK/실제 CAD 엔진이다. ezdxf 자체를 DWG writer라고 표현하지 않는다. 공식 [ezdxf 문서](https://ezdxf.readthedocs.io/en/stable/introduction.html)와 [ODA 변환기](https://www.opendesign.com/guestfiles/oda_file_converter)를 참조한다.

확장자만 바꾼 DWG, 빈 파일, raster attachment만 포함한 결과는 실패다. 실제 target CAD 버전은 미확정이며 converter 설치 확인은 호환성 증거가 아니다. 모델 지표와 별개로 `DXF export`, `DWG convert`, `CAD open`, `entity edit`, `save/reopen`, `render-back` receipt를 각각 남긴다. conversion crash·timeout·외부참조 누락도 전체 입력 분모에 포함한다.

## 중심선·치수 생성 계약

중심선/연결 그래프를 먼저 구성하고 승인된 치수 원장으로 전체 구조를 제약한 뒤 벽 두께·개구부·디테일을 작성한다. 중심선과 마감면 측정 기준·offset을 명시한다. 필요한 모든 치수의 출력 대응과 실제 endpoint 길이/투영 길이를 검증하며 text 보존/override만으로 통과시키지 않는다. 후속 반전 기능을 만들 경우 geometry/치수 관계/문 방향에 적용하고 문자는 읽을 수 있게 생성한다. 실제 반전 판별은 기본 복원의 선행 조건이 아니다. [상세 계획](research/2026-10-13-vector-first-training-plan.md)을 따른다.

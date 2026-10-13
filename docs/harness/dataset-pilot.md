# 데이터 pilot 실행·검수 안내

현재 구현 범위는 의뢰 연결 폴더의 파일 발견, 로컬 복사본 변경전 crop, ODA DWG export/reopen, 치수 대조, 자동 homography 진단과 비공개 HTML 검수 화면이다. 모델 학습·canonical CAD solver·실제 CAD 사용자 수정/저장은 포함되지 않는다.

## 환경과 입력

Python 3.14 실행 환경에서 `requirements-pilot.txt`를 설치해 검증했다. ODA executable과 기존 data-pipeline `dwg_crop/pipeline.py`는 로컬 config의 `cad_converter_executable`, `crop_detector_module`로 지정한다. 기존 detector의 SHA-256을 sample receipt에 기록하며 변경한 모듈로 결과를 재현했다고 가정하지 않는다.

의뢰 인덱스는 운영 워크 `GET /api/agent/folders`의 authorized snapshot이다. 이번에는 기존 로컬 credential로 운영 API 접근이 실패해 운영 컨테이너 내부에서 동일 read-only GET을 호출했다. credential은 파일/로그에 기록하지 않는다. 개발 DB의 소량 case 목록을 운영 인덱스와 혼동하지 않는다.

실제 source paths·case index·dataset/output root는 `configs/paths.local.json`과 ignored `local/`, `outputs/`에만 둔다. 다른 저장소/원본에 데이터를 쓰거나 변경하지 않는다. 전체 공유폴더 recursive scan 대신 연결 폴더의 immediate children만 본다.

## 순서

1. `scripts/discover_pilot.py --index <private-index> --output <private-output> --wanted 60 --max-folders 1500`
2. `scripts/build_pilot.py --output <private-output> --source-module <detector-module> --converter <ODA-executable> --target 40 --max-attempts 50`
3. `scripts/refresh_renders.py --root <private-output> --source-module <detector-module> --converter <ODA-executable>`
4. `scripts/sheet_previews.py --root <private-output> --source-module <detector-module> --converter <ODA-executable>`
5. `scripts/audit_cad.py --root <private-output>`
6. `scripts/build_review.py --root <private-output>`

각각 프로젝트 pilot 환경의 Python으로 실행한다. worker는 순차 실행하고 100초 timeout, sample receipt 기반 resume을 지원한다. sample ID는 discovery의 고정 순서와 연결된다. 같은 output directory에 다른 discovery를 덮어쓰지 말고 새 run ID를 사용한다. refresh는 exact resolution 검증된 receipt를 재사용하며 바뀐 등록 protocol을 시험하려면 새 run을 사용한다.

## 검수 화면

private output의 `review.html`을 열거나 다음 명령으로 loopback에서 보여준다.

```powershell
.venv/Scripts/python.exe -m http.server 8765 --bind 127.0.0.1 --directory outputs/pilot-2026-10-13
```

브라우저에서 `http://127.0.0.1:8765/review.html`을 연다. 기본 비교는 준공도면과 DWG 재열기 CAD다. 전체 source CAD+빨간 crop 박스, source crop, feature matches, 검증된 자동 정합 결과가 있는 경우 overlay를 전환한다. 확대/스크롤·대응점 기록·영역/정합/치수 판정·메모·JSON 내보내기를 제공한다.

검수 선택은 browser localStorage에만 저장되며 manifest를 자동 승인하지 않는다. 내보낸 human review JSON을 검토해 별도 승인 version으로 반영해야 한다. reviewer 이름·근거와 unit/anchor를 확인한 뒤 gold로 분류한다. UI에서 사용한 클릭 좌표는 preview pixel 좌표이며 원본 이미지/CAD 좌표와 다르다.

## 체크와 한계

`python -m unittest discover -s tests -v`: 정확한 파일명·비재귀 발견, 치수 누락/스타일 변경 검출, 없는 치수의 가짜 pass 방지, 실제 render resolution, known homography, HEADER HANDSEED와 entity handle 구분을 검사한다.

DIMENSION multiset 대조는 원본 DWG→crop/export 보존 검사다. 준공도면에 쓰인 숫자와 DWG 숫자가 같다는 검증을 대체하지 않는다. feature fitting 잔차도 independent landmark/mm accuracy가 아니다. 자동 정합이 실패해도 무리한 warp를 승인하지 않는다. raw DXF handle collision/loader 경고를 별도 표시하고 `doc.audit()`가 error 0이라고 모든 문서 무결성을 확정하지 않는다.

진단 산출물은 연구·검수 준비 자료다. 승인되지 않은 페어를 hard supervised train에 넣지 않는다. 원본/도면을 공개 Git 또는 외부 모델 API에 올리지 않는다.

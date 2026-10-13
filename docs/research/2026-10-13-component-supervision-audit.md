# CAD 컴포넌트 구조 감사와 학습 단위 수정

작성일: 2026-10-13 KST. 기존 pilot의 로컬 source/before/reopened DXF 120개를 읽었다. source DXF는 원본 DWG의 ODA 변환 사본이며 이번에 공유폴더 원본을 다시 변환하거나 수정하지 않았다. 모델 학습·원본 편집·block explode는 실행하지 않았다.

## 결론

매 CAD LINE을 준공도면의 선과 1:1 대응시키는 학습이 목표가 아니다. **업무 컴포넌트의 종류·배치·치수 parameter·관계를 감독하고, CAD builder가 엔티티를 작성하는 표현**으로 정정한다. DINOv3 encoder 후보 선택은 유지하되 기존 junction/edge 중심 decoder는 컴포넌트/관계 head와 내부 geometry head로 구체화하기 전 학습에 투입하지 않는다.

모델 loss에서 예측 객체와 GT 객체를 대응시키는 set matching은 남을 수 있다. 그 대응 단위는 검수된 문/벽 구간/치수 등의 객체다. 입력 이미지의 모든 획과 저장 LINE handle을 강제로 맞추는 것은 아니다. 랜덤 handle·block 이름·entity 저장 순서는 학습 정답 identity로 쓰지 않는다.

## 1. 실제 조사 결과

[공개 집계](assets/2026-10-13-component-summary.json)는 실제 inventory에서 추출했다. 세부 block/layer/좌표·문자·관계는 Git 제외된 `outputs/components-2026-10-13/inventory.json`에 있다. 표의 count는 40개 파일 합계이며 고유 컴포넌트 종류 수가 아니다.

| 항목 | source 전체 modelspace | 변경전 crop | DWG 재열기 |
| --- | ---: | ---: | ---: |
| LINE | 49,123 | 22,505 | 22,505 |
| LWPOLYLINE | 14,053 | 5,859 | 5,859 |
| DIMENSION | 1,826 | 913 | 913 |
| INSERT | 151 | 76 | 76 |
| ARC | 869 | 369 | 369 |
| HATCH | 1,394 | 640 | 640 |
| MLINE | 106 | 47 | 47 |
| TEXT + MTEXT | 4,036 | 918 | 918 |
| modelspace INSERT가 있는 파일 | 13 / 40 | 13 / 40 | 13 / 40 |
| 명시적 GROUP이 있는 파일 | 0 / 40 | 0 / 40 | 0 / 40 |
| DIMASSOC object | 992 | 700 | 700 |

변경전 913개 DIMENSION 모두 graphical picture block을 가진다. 이를 그림으로 풀면 LINE·문자·화살표가 나오지만 치수 913개를 많은 독립 선으로 감독하지 않는다. definition point·type·style/override·measurement를 유지한다. 이번 표본에서 DIMENSION text의 비기본 override는 0개였으며 style override·scale까지 없다는 뜻은 아니다. [DIMENSION 공식 문서](https://ezdxf.readthedocs.io/en/stable/dxfentities/dimension.html)

변경전에는 파일별 block definition 합계 3,543개가 저장돼 있지만 modelspace INSERT/DIMENSION에서 nested reference를 따라 도달한 definition은 합계 981개다. 이 탐색은 dimstyle arrow reference·객체 dictionary 등 모든 참조 경로를 포함하지 않는다. 정의의 존재, 현재 평면의 배치, 의미가 서로 다르다. 원본 도곽/템플릿/사용하지 않는 정의가 학습 객체에 섞이지 않게 해야 한다. [INSERT 공식 문서](https://ezdxf.readthedocs.io/en/stable/blocks/insert.html)

예를 들어 S001 변경전은 modelspace INSERT 없이 LINE/LWPOLYLINE/ARC/MLINE/HATCH/문자와 native DIMENSION으로 구성돼 있다. S020은 복합 도형을 담은 INSERT 1개를 사용한다. 구조적 컴포넌트가 반드시 명시적 BLOCK/GROUP으로 저장되는 것은 아니다. 재사용 후 분해/복사한 도형도 고려해야 한다.

레이어도 의미를 단독 확정하지 못한다. 실제 CEN에는 LINE과 DIMENSION이 함께 있고, WIN에는 polyline/line/arc/insert, TEX1에는 문자 외의 geometry가 있다. DOOR 레이어가 있는 표본에서도 LINE/LWPOLYLINE/ARC 조합을 확인했다. layer 이름은 grouping 근거이며 최종 문·창·벽 의미 정답은 형상·주변 관계와 검수로 확정한다.

DIMASSOC object 700개와 reactor를 가진 DIMENSION 303개를 확인했다. 이것만으로 700개의 유효 치수 관계 또는 303개의 정상 wall association을 확정할 수 없다. reference target의 생존/종류·crop 경계·reactor 무결성은 별도 검사해야 한다. 단순 endpoint 근접을 확정 association으로 대신하지 않는다.

120개 로컬 입력의 SHA-256/size/mtime가 이번 분석 전후 동일했다. 기존 pilot report/manifest/receipt는 수정하지 않았다. 이 분석은 모든 DWG 작성 프로그램의 원래 authoring semantics나 proxy/dynamic 객체를 완전히 해석한 결과가 아니다.

## 2. 학습 정답의 계층

| 계층 | 역할 | 보존/학습 범위 |
| --- | --- | --- |
| Native CAD | BLOCK/INSERT·DIMENSION·style·group·raw entities | 원래 구조와 instance transform, dependencies, source handle provenance를 보존 |
| 업무 컴포넌트 | 벽 구간·문·창·공간 경계·치수·문자 | 모델의 주된 예측/검수 단위. native ID가 없으면 묶음 후보를 만들고 검수 |
| 관계/제약 | wall junction·opening host·공간 경계·dimension refs | 치수대로 geometry를 구성하는 감독과 solver 입력 |
| Geometry/compiler | LINE/POLYLINE/ARC/HATCH/INSERT/DIMENSION | 지원 컴포넌트를 엔티티로 생성. 미지원 잔여 선은 명시적으로 보존/검수 |

동일한 문이 하나의 BLOCK 또는 여러 LINE+ARC로 저장돼도 같은 업무 컴포넌트로 정규화할 수 있다. 원본 표현은 provenance로 유지한다. 서로 다른 문/창/벽을 공유 layer라는 이유만으로 같은 컴포넌트로 합치지 않는다.

## 3. 초기 컴포넌트 계약 제안

아래는 초기 후보이며 실제 component catalog 검수와 factory roundtrip 후 고정한다.

- `wall_segment`: 중심선/양면 경계·길이·두께·접합부·layer. 비내력 속성은 직원 확정 근거가 있을 때만 연결한다.
- `door`: host wall·offset·폭·경첩·열림 방향·검수 template ID. 기존 블록은 reuse하고 분해된 LINE+ARC는 shape/host 근거로 묶는다.
- `window`: host·위치·폭·세부 형식. 검수한 block 또는 parameterized polyline assembly로 생성한다.
- `space/balcony`: 경계·인접 공간·개구부·검수 용도. 닫힌 polyline이나 hatch만으로 베란다 의미를 확정하지 않는다.
- `dimension`: kind·측정 대상/점·value/unit·치수선 위치·style/override. native DIMENSION으로 출력하고 실제 geometry measurement와 비교한다.
- `text`: content·anchor·rotation·style·연관 공간/치수. 치수 객체 내부의 표시 문자와 독립 공간 문자를 중복 학습하지 않는다.
- `custom/unresolved`: 미해석 block/proxy·잔여 geometry. 지원 실패를 버려서 완료 처리하지 않는다.

builder는 검수 component type+parameter를 입력받아 편집 가능한 CAD 객체를 만든다. 도면마다 임의 block 이름을 외우는 모델을 만들지 않는다. 문 template 선택과 길이/폭 회귀, wall/opening/dimension 관계는 분리해 검사한다. instance의 local geometry와 배치 transform을 분리하고 같은 정의를 반복 저장하지 않는다.

## 4. 수정된 다음 구현 순서

1. **컴포넌트 catalog:** 이번 40개 inventory를 이용해 반복 block/분해된 도형/치수/레이어 profile의 대표를 선택한다. 문·창·벽·베란다·문자·미해석 요소를 시각 확인하고 유형·parameter·원본 멤버·관계·불확실성을 기록한다. 저장 attribute signature는 불완전 fingerprint이며 자동 의미 clustering 정답으로 쓰지 않는다.
2. **치수 관계 검사:** DIMASSOC/reactor를 가능한 범위에서 읽고 reference 생존과 측정점/entity 일치를 검증한다. 없는 관계는 후보+검수로 보충한다. 전체 association이 존재한다고 가정하지 않는다.
3. **component factory와 GT roundtrip:** 5개 debug CAD의 검수 컴포넌트를 재배치/조립해 DXF/DWG를 만들고 치수·문 방향·레이어·개구부·편집성을 검증한다. 원본 재저장 성공과 컴포넌트 재구성 성공을 구분한다.
4. **그 정답으로 첫 학습:** DINOv3 + component type/parameter/relationship heads, 필요 시 내부 junction/geometry head를 학습한다. Raster2Seq는 동일 공통 출력 검증을 거치는 topology 비교다. 공개 polygon output만으로 사내 component 복원 성공을 선언하지 않는다.
5. **합성→실제→HITL:** 검수 component CAD로 합성 감독을 만들고 실제 준공도면 fine-tune과 국소 수정으로 확장한다. 전유부/치수 정확한 DWG가 핵심이며 실제 반전은 여전히 후속 CAD 편집이다.

문 type/벽 구간 등 컴포넌트 대응을 학습하는 set matching과 입력/CAD의 전역 특징점 정합은 서로 다른 문제다. 전체 특징점 정합 재시도는 중단 상태를 유지한다. 이번 변경은 핵심 목표를 바꾸는 것이 아니라 학습 정답과 writer를 실제 사내 CAD 구조에 맞추는 것이다.

## 재현

```powershell
.\.venv\Scripts\python.exe scripts/analyze_cad_components.py --samples <private-pilot-samples> --output <new-private-run>
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_components.py -v
```

분석기는 source/before/reopened 로컬 사본만 읽고 source document를 save/explode하지 않는다. 상세 inventory·layer/block names·문자/좌표·gallery는 비공개다. 이번 audit는 component 의미 확정·factory 구현·모델 학습 성과가 아니다.

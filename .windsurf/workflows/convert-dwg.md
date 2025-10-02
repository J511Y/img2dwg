---
description: DWG 파일을 중간 표현 JSON 형태로 변환하는 워크플로우입니다.
auto_execution_mode: 3
---

# Convert DWG Workflow

DWG 파일을 중간 표현 JSON 형태로 변환하는 워크플로우입니다.

## 작업 순서

1. **DXF 변환 도구 확인**
   - ODAFileConverter 또는 AutoCAD 설치 여부 확인
   - 변환 도구 경로 설정

2. **DWG→DXF 변환**
   - 스캔된 DWG 파일 목록 읽기
   - 각 DWG 파일을 DXF로 변환
   - 변환 실패한 파일 로깅

3. **DXF 파싱**
   - `ezdxf` 라이브러리를 사용하여 DXF 파일 읽기
   - 엔티티 추출:
     - LINE (직선)
     - LWPOLYLINE (폴리라인)
     - CIRCLE (원)
     - ARC (호)
     - TEXT (텍스트)
     - DIMENSION (치수)

4. **JSON 변환**
   - 추출한 엔티티를 JSON 스키마에 맞게 변환
   - 좌표계 정규화 (스케일 통일)
   - 레이어 정보 포함

5. **검증**
   - JSON 스키마 유효성 검증
   - 필수 필드 확인 (metadata, entities)

6. **저장**
   - `output/json/{project_name}_{type}.json` 형식으로 저장
   - 변환 로그 저장 (`output/conversion_log.txt`)

## 실행 명령어

```bash
python scripts/convert_dwg.py --input datas/ --output output/json/
```

## 중간 표현 JSON 예시

```json
{
  "metadata": {
    "filename": "변경전후.dwg",
    "type": "변경",
    "project": "이매촌 진흥 814-405",
    "source_path": "datas/2501 (2)/이매촌 진흥 814-405/변경전후.dwg"
  },
  "entities": [
    {
      "type": "line",
      "start": {"x": 0.0, "y": 0.0},
      "end": {"x": 3500.0, "y": 0.0},
      "layer": "Wall",
      "color": 7,
      "linetype": "Continuous"
    },
    {
      "type": "polyline",
      "points": [
        {"x": 0.0, "y": 0.0},
        {"x": 1000.0, "y": 0.0},
        {"x": 1000.0, "y": 2000.0}
      ],
      "closed": true,
      "layer": "Furniture"
    },
    {
      "type": "text",
      "position": {"x": 1750.0, "y": 1000.0},
      "content": "거실",
      "height": 250.0,
      "layer": "Text"
    }
  ]
}
```

## 오류 처리

- DWG 파일이 손상된 경우: 로그에 기록하고 건너뛰기
- DXF 변환 실패: 오류 메시지와 함께 로그 저장
- 지원하지 않는 엔티티: 경고 출력 및 무시

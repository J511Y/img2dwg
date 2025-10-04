"""토큰 카운팅 테스트 스크립트."""

import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import tiktoken


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """텍스트의 토큰 수를 계산한다."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def main():
    """토큰 카운팅 테스트."""
    print("=" * 60)
    print("토큰 카운팅 테스트")
    print("=" * 60)

    # 예제 레코드 (간단한 버전)
    sample_record = {
        "messages": [
            {
                "role": "system",
                "content": "당신은 2D 건축 평면도 이미지를 분석하는 전문가입니다."
            },
            {
                "role": "user",
                "content": "평면도를 분석해주세요."
            },
            {
                "role": "assistant",
                "content": json.dumps({
                    "metadata": {
                        "filename": "test.dwg",
                        "entity_count": 10
                    },
                    "entities": [
                        {"type": "line", "start": {"x": 0, "y": 0}, "end": {"x": 100, "y": 100}}
                    ]
                })
            }
        ]
    }

    # JSON 문자열로 변환
    record_str = json.dumps(sample_record, ensure_ascii=False)

    # 토큰 수 계산
    token_count = count_tokens(record_str)

    print(f"\n샘플 레코드:")
    print(f"- 문자 수: {len(record_str):,}")
    print(f"- 토큰 수: {token_count:,}")
    print(f"- 60,000 토큰 제한: {'✅ 통과' if token_count <= 60000 else '❌ 초과'}")

    # 실제 파일이 있다면 테스트
    converted_json = project_root / "output" / "examples" / "converted.json"
    if converted_json.exists():
        print(f"\n실제 변환 파일 테스트:")
        print(f"파일: {converted_json}")

        with open(converted_json, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # 간단한 레코드 생성
        test_record = {
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 2D 건축 평면도 이미지를 분석하여 AutoCAD 호환 JSON 형태로 변환하는 전문가입니다."
                },
                {
                    "role": "user",
                    "content": "평면도 이미지를 분석해주세요."
                },
                {
                    "role": "assistant",
                    "content": json.dumps(json_data, ensure_ascii=False)
                }
            ]
        }

        test_str = json.dumps(test_record, ensure_ascii=False)
        test_tokens = count_tokens(test_str)

        print(f"- 엔티티 수: {json_data['metadata']['original_entities']:,}")
        print(f"- 문자 수: {len(test_str):,}")
        print(f"- 토큰 수: {test_tokens:,}")
        print(f"- 60,000 토큰 제한: {'✅ 통과' if test_tokens <= 60000 else '❌ 초과'}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

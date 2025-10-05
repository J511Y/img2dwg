#!/usr/bin/env python
# coding=utf-8
"""img2dwg 데이터셋을 Qwen2.5-VL 파인튜닝 포맷으로 변환하는 스크립트."""

import json
import os
from pathlib import Path
import argparse
from tqdm import tqdm

def convert_entry(entry):
    """단일 데이터 항목을 변환합니다."""
    raw_messages = entry["messages"]
    
    system_prompt = ""
    if raw_messages[0]["role"] == "system":
        system_prompt = raw_messages[0]["content"] + "\n\n"
        raw_messages = raw_messages[1:]

    conversations = []
    images = []
    
    # User 메시지 처리
    user_msg = raw_messages[0]
    assert user_msg["role"] == "user", "First message after system must be from user"
    
    user_content = user_msg["content"]
    user_text = ""
    if isinstance(user_content, list):
        for item in user_content:
            if item["type"] == "text":
                user_text += item["text"]
            elif item["type"] == "image_url":
                # URL에서 파일 이름만 추출하여 리스트에 추가
                images.append(os.path.basename(item["image_url"]["url"]))
    else:
        user_text = user_content

    # 시스템 프롬프트와 user 텍스트 결합
    # 이미지 토큰을 텍스트 앞쪽에 추가
    image_tokens = DEFAULT_IMAGE_TOKEN * len(images)
    full_user_text = f"{image_tokens}\n{system_prompt}{user_text}"
    
    conversations.append({"from": "human", "value": full_user_text})

    # Assistant 메시지 처리
    assistant_msg = raw_messages[1]
    assert assistant_msg["role"] == "assistant", "Second message must be from assistant"
    
    conversations.append({"from": "gpt", "value": assistant_msg["content"]})

    # Qwen-VL 포맷으로 변환
    return {
        "id": entry.get("id", os.path.splitext(images[0])[0] if images else "no_id"),
        "image": images,
        "conversations": conversations
    }

def main():
    """메인 변환 함수."""
    parser = argparse.ArgumentParser(description="Convert dataset to Qwen-VL format.")
    parser.add_argument("--input_file", type=str, required=True, help="Input JSONL file path.")
    parser.add_argument("--output_file", type=str, required=True, help="Output JSON file path.")
    args = parser.parse_args()

    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output_file}")

    converted_data = []
    with open(args.input_file, "r") as f_in:
        for line in tqdm(f_in, desc="Converting data"):
            entry = json.loads(line)
            converted_entry = convert_entry(entry)
            converted_data.append(converted_entry)

    # 출력 디렉토리 생성
    Path(args.output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(args.output_file, "w") as f_out:
        json.dump(converted_data, f_out, indent=2, ensure_ascii=False)

    print(f"\nSuccessfully converted {len(converted_data)} entries.")
    print(f"Output saved to: {args.output_file}")

if __name__ == "__main__":
    DEFAULT_IMAGE_TOKEN = "<image>"
    main()


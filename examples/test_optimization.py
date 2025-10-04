"""최적화 옵션 테스트 스크립트."""

import sys
from pathlib import Path
import json

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.data.dwg_parser import DWGParser, ParseOptions
import tiktoken


def count_tokens(data: dict) -> int:
    """JSON 데이터의 토큰 수를 계산한다."""
    try:
        encoding = tiktoken.encoding_for_model("gpt-4o")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    json_str = json.dumps(data, ensure_ascii=False)
    return len(encoding.encode(json_str))


def test_dwg_file(dwg_path: Path):
    """DWG 파일을 다양한 옵션으로 테스트한다."""
    print("=" * 80)
    print(f"테스트 파일: {dwg_path.name}")
    print("=" * 80)
    
    if not dwg_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {dwg_path}")
        return
    
    # 테스트 설정들
    configs = [
        ("기본 (최적화 없음)", ParseOptions(
            round_ndigits=None,
            drop_defaults=False,
            rdp_tolerance=None,
            dxf_version="R2018",
        )),
        ("기본 최적화", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            dxf_version="R2000",
        )),
        ("RDP 간소화 (보수적)", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=0.5,
            dxf_version="R2000",
        )),
        ("RDP 간소화 (중간)", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=1.0,
            dxf_version="R2000",
        )),
        ("RDP 간소화 (공격적)", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=2.0,
            dxf_version="R2000",
        )),
        ("Compact 스키마", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=1.0,
            compact_schema=True,
            dxf_version="R2000",
        )),
        ("Compact + 공격적 RDP", ParseOptions(
            round_ndigits=3,
            drop_defaults=True,
            rdp_tolerance=2.0,
            compact_schema=True,
            dxf_version="R2000",
        )),
        ("그리드 양자화", ParseOptions(
            quantize_grid=1.0,
            drop_defaults=True,
            rdp_tolerance=1.0,
            dxf_version="R2000",
        )),
    ]
    
    print(f"\n{'설정':<25} {'엔티티':<10} {'토큰':<12} {'JSON(KB)':<10} {'절감율'}")
    print("-" * 80)
    
    baseline_tokens = None
    
    for config_name, options in configs:
        try:
            parser = DWGParser(options=options)
            result = parser.parse(dwg_path)
            
            entity_count = len(result.get("entities", []))
            token_count = count_tokens(result)
            json_str = json.dumps(result, ensure_ascii=False)
            json_kb = len(json_str.encode('utf-8')) / 1024
            
            if baseline_tokens is None:
                baseline_tokens = token_count
                reduction = "-"
            else:
                reduction = f"{(1 - token_count / baseline_tokens) * 100:>5.1f}%"
            
            status = "✅" if token_count <= 60000 else "⚠️"
            
            print(
                f"{config_name:<25} "
                f"{entity_count:<10,} "
                f"{token_count:<12,} "
                f"{json_kb:<10.2f} "
                f"{reduction} {status}"
            )
            
        except Exception as e:
            print(f"{config_name:<25} ❌ 실패: {e}")
    
    print("\n범례:")
    print("  ✅ = 60k 토큰 이하 (파인튜닝 가능)")
    print("  ⚠️  = 60k 토큰 초과 (타일링 필요)")
    print()


def main():
    """메인 함수."""
    # 테스트할 DWG 파일 경로 (실제 경로로 변경 필요)
    test_files = [
        project_root / "datas" / "sample.dwg",  # 예시 경로
        # 추가 테스트 파일...
    ]
    
    # datas 폴더에서 첫 번째 DWG 파일 찾기
    datas_dir = project_root / "datas"
    if datas_dir.exists():
        dwg_files = list(datas_dir.rglob("*.dwg"))
        if dwg_files:
            test_files = [dwg_files[0]]  # 첫 번째 파일만 테스트
            print(f"발견된 DWG 파일: {len(dwg_files)}개")
            print(f"테스트 파일: {test_files[0]}\n")
    
    for dwg_path in test_files:
        if dwg_path.exists():
            test_dwg_file(dwg_path)
            break
    else:
        print("테스트할 DWG 파일이 없습니다.")
        print(f"datas 폴더에 DWG 파일을 추가하거나,")
        print(f"이 스크립트의 test_files 변수를 수정하세요.")


if __name__ == "__main__":
    main()

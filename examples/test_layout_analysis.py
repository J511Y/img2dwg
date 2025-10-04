"""레이아웃 분석 효과 테스트 스크립트."""

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
    """DWG 파일을 레이아웃 분석으로 테스트한다."""
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
            dxf_version="R2018",
        )),
        ("RDP + Compact", ParseOptions(
            rdp_tolerance=1.0,
            round_ndigits=3,
            drop_defaults=True,
            compact_schema=True,
            dxf_version="R2000",
        )),
        ("🚀 레이아웃 분석 (권장)", ParseOptions(
            rdp_tolerance=1.0,
            round_ndigits=3,
            drop_defaults=True,
            use_layout_analysis=True,
            dxf_version="R2000",
        )),
    ]
    
    print(f"\n{'설정':<30} {'엔티티/객체':<15} {'토큰':<12} {'JSON(KB)':<10} {'절감율'}")
    print("-" * 90)
    
    baseline_tokens = None
    
    for config_name, options in configs:
        try:
            parser = DWGParser(options=options)
            result = parser.parse(dwg_path)
            
            # 엔티티/객체 수 계산
            if "layout" in result:
                # 레이아웃 분석 모드
                layout = result["layout"]
                obj_count = (
                    len(layout.get("walls", [])) +
                    len(layout.get("rooms", [])) +
                    len(layout.get("openings", [])) +
                    len(layout.get("annotations", []))
                )
                obj_type = "객체"
            else:
                # 일반 모드
                obj_count = len(result.get("entities", []))
                obj_type = "엔티티"
            
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
                f"{config_name:<30} "
                f"{obj_count:>6,} {obj_type:<8} "
                f"{token_count:<12,} "
                f"{json_kb:<10.2f} "
                f"{reduction} {status}"
            )
            
            # 레이아웃 분석 상세 정보
            if "layout" in result:
                metadata = result.get("metadata", {})
                print(f"  └─ 압축률: {metadata.get('compression_ratio', 0)}% | "
                      f"벽: {len(layout.get('walls', []))} | "
                      f"방: {len(layout.get('rooms', []))} | "
                      f"개구부: {len(layout.get('openings', []))} | "
                      f"주석: {len(layout.get('annotations', []))}")
            
        except Exception as e:
            print(f"{config_name:<30} ❌ 실패: {e}")
    
    print("\n범례:")
    print("  ✅ = 60k 토큰 이하 (파인튜닝 가능)")
    print("  ⚠️  = 60k 토큰 초과")
    print("\n💡 권장: --layout-analysis 옵션 사용")
    print()


def main():
    """메인 함수."""
    # datas 폴더에서 첫 번째 DWG 파일 찾기
    datas_dir = project_root / "datas"
    
    if not datas_dir.exists():
        print(f"❌ datas 폴더가 없습니다: {datas_dir}")
        print("테스트할 DWG 파일을 datas 폴더에 추가하세요.")
        return
    
    dwg_files = list(datas_dir.rglob("*.dwg"))
    
    if not dwg_files:
        print("❌ DWG 파일을 찾을 수 없습니다.")
        print(f"datas 폴더에 DWG 파일을 추가하세요: {datas_dir}")
        return
    
    print(f"발견된 DWG 파일: {len(dwg_files)}개\n")
    
    # 첫 번째 파일 테스트
    test_dwg_file(dwg_files[0])
    
    # 추가 파일이 있으면 간단히 표시
    if len(dwg_files) > 1:
        print(f"\n추가 파일 {len(dwg_files) - 1}개:")
        for dwg in dwg_files[1:6]:  # 최대 5개만
            print(f"  - {dwg.name}")
        if len(dwg_files) > 6:
            print(f"  ... 외 {len(dwg_files) - 6}개")


if __name__ == "__main__":
    main()

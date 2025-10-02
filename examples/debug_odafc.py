"""ODAFileConverter 디버깅 스크립트."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import ezdxf
from ezdxf.addons import odafc
from ezdxf import options


def main():
    """ODAFileConverter 설정을 디버깅한다."""
    print("=" * 60)
    print("ODAFileConverter 디버깅")
    print("=" * 60)
    
    # 1. ezdxf 옵션 확인
    print("\n[1] ezdxf options 확인")
    print(f"   options 타입: {type(options)}")
    print(f"   options dir: {[x for x in dir(options) if not x.startswith('_')][:10]}")
    
    # 2. odafc 설정 확인
    print("\n[2] odafc 설정 확인")
    try:
        # odafc의 내부 설정 확인
        from ezdxf.addons.odafc import _config
        print(f"   _config: {_config}")
    except ImportError as e:
        print(f"   _config import 실패: {e}")
    
    # 3. win_exec_path 직접 읽기
    print("\n[3] win_exec_path 직접 읽기")
    win_path = options.get("odafc-addon", "win_exec_path")
    print(f"   win_exec_path: {win_path}")
    
    if win_path:
        win_path_obj = Path(win_path)
        print(f"   경로 존재: {win_path_obj.exists()}")
        print(f"   실행 가능: {win_path_obj.is_file()}")
    
    # 4. is_installed() 함수 소스 확인
    print("\n[4] is_installed() 함수 확인")
    print(f"   결과: {odafc.is_installed()}")
    
    # 5. 직접 실행 가능 여부 확인
    print("\n[5] 직접 실행 테스트")
    if win_path:
        import subprocess
        try:
            result = subprocess.run(
                [win_path, "--help"],
                capture_output=True,
                timeout=5
            )
            print(f"   실행 성공! 종료 코드: {result.returncode}")
            print(f"   출력: {result.stdout.decode('utf-8', errors='ignore')[:200]}")
        except FileNotFoundError:
            print(f"   ❌ 실행 파일을 찾을 수 없음")
        except subprocess.TimeoutExpired:
            print(f"   ⏱️  타임아웃 (GUI가 열렸을 수 있음)")
        except Exception as e:
            print(f"   ❌ 실행 오류: {e}")
    
    # 6. 모든 섹션 출력
    print("\n[6] 전체 config 섹션")
    for section in options.sections():
        print(f"   [{section}]")
        for key, value in options.items(section):
            print(f"      {key} = {value}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

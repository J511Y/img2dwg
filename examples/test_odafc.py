"""ODAFileConverter 설치 및 설정 테스트 스크립트."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ezdxf.addons import odafc


def main():
    """ODAFileConverter 설정을 확인한다."""
    print("=" * 60)
    print("ODAFileConverter 설정 확인")
    print("=" * 60)
    
    # 1. 설치 여부 확인
    print("\n[1] 설치 여부 확인")
    is_installed = odafc.is_installed()
    print(f"   설치됨: {is_installed}")
    
    # 2. 설정 파일 위치 확인
    print("\n[2] .ezdxfrc 파일 확인")
    
    # 프로젝트 루트
    project_rc = project_root / ".ezdxfrc"
    print(f"   프로젝트 루트: {project_rc}")
    print(f"   존재: {project_rc.exists()}")
    if project_rc.exists():
        print(f"   내용:")
        with open(project_rc, "r", encoding="utf-8") as f:
            for line in f:
                print(f"      {line.rstrip()}")
    
    # 홈 디렉토리
    home_rc = Path.home() / ".ezdxfrc"
    print(f"\n   홈 디렉토리: {home_rc}")
    print(f"   존재: {home_rc.exists()}")
    if home_rc.exists():
        print(f"   내용:")
        with open(home_rc, "r", encoding="utf-8") as f:
            for line in f:
                print(f"      {line.rstrip()}")
    
    # 3. ODAFileConverter 실행 파일 확인
    print("\n[3] ODAFileConverter 실행 파일 확인")
    oda_paths = [
        Path("C:/Program Files/ODA/ODAFileConverter 26.8.0/ODAFileConverter.exe"),
        Path("C:/Program Files (x86)/ODA/ODAFileConverter 26.8.0/ODAFileConverter.exe"),
    ]
    
    for oda_path in oda_paths:
        print(f"   {oda_path}")
        print(f"   존재: {oda_path.exists()}")
    
    # 4. ezdxf 버전 확인
    print("\n[4] ezdxf 버전")
    import ezdxf
    print(f"   버전: {ezdxf.version}")
    print(f"   설치 경로: {Path(ezdxf.__file__).parent}")
    
    # 5. 권장 사항
    print("\n" + "=" * 60)
    if not is_installed:
        print("⚠️  ODAFileConverter를 찾을 수 없습니다!")
        print("\n해결 방법:")
        print("1. 홈 디렉토리에 .ezdxfrc 파일 생성:")
        print(f"   {home_rc}")
        print("\n2. 파일 내용:")
        print("   [odafc-addon]")
        print("   win_exec_path = C:/Program Files/ODA/ODAFileConverter 26.8.0/ODAFileConverter.exe")
        print("\n3. 또는 아래 명령어 실행:")
        print(f'   copy "{project_rc}" "{home_rc}"')
    else:
        print("✅ ODAFileConverter가 정상적으로 설정되었습니다!")
    print("=" * 60)


if __name__ == "__main__":
    main()

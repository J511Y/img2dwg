"""이미지 업로드 테스트 스크립트."""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from img2dwg.utils.image_uploader import ImageUploader, URLCache


def test_upload(service: str = "imgur"):
    """
    이미지 업로드를 테스트한다.

    Args:
        service: 업로드 서비스 (imgur, github, cloudinary)
    """
    print("=" * 80)
    print(f"이미지 업로드 테스트 - {service.upper()}")
    print("=" * 80)

    # 테스트 이미지 찾기
    datas_dir = project_root / "datas"
    if not datas_dir.exists():
        print(f"❌ datas 폴더가 없습니다: {datas_dir}")
        print("테스트할 이미지를 datas 폴더에 추가하세요.")
        return

    # 첫 번째 이미지 찾기
    image_files = list(datas_dir.rglob("*.jpg")) + list(datas_dir.rglob("*.png"))
    if not image_files:
        print("❌ 이미지 파일을 찾을 수 없습니다.")
        print(f"datas 폴더에 이미지를 추가하세요: {datas_dir}")
        return

    test_image = image_files[0]
    print(f"\n테스트 이미지: {test_image.name}")
    print(f"크기: {test_image.stat().st_size / 1024:.1f} KB")

    # 업로더 초기화
    try:
        uploader = ImageUploader(service=service)
        print(f"\n✅ {service} 업로더 초기화 완료")
    except Exception as e:
        print(f"\n❌ 업로더 초기화 실패: {e}")
        print("\n환경변수를 설정하세요:")
        if service == "imgur":
            print("  $env:IMGUR_CLIENT_ID=\"your_client_id\"  # Windows")
            print("  export IMGUR_CLIENT_ID=\"your_client_id\"  # Linux/Mac")
            print("\nImgur Client ID 발급: https://api.imgur.com/oauth2/addclient")
        elif service == "github":
            print("  $env:GITHUB_TOKEN=\"ghp_xxx\"")
            print("  $env:GITHUB_REPO_OWNER=\"username\"")
            print("  $env:GITHUB_REPO_NAME=\"img2dwg-images\"")
            print("\nGitHub Token 발급: https://github.com/settings/tokens")
        elif service == "cloudinary":
            print("  $env:CLOUDINARY_URL=\"cloudinary://API_KEY:API_SECRET@CLOUD_NAME\"")
            print("\nCloudinary 가입: https://cloudinary.com/")
        return

    # 캐시 초기화
    cache_file = project_root / "output" / "test_image_cache.json"
    cache = URLCache(cache_file)

    # 캐시 확인
    cached_url = cache.get(test_image)
    if cached_url:
        print(f"\n📦 캐시된 URL 발견:")
        print(f"   {cached_url}")
        print("\n캐시를 사용하시겠습니까? (y/n)")
        use_cache = input("> ").strip().lower()
        if use_cache == "y":
            print(f"\n✅ 캐시 URL 사용: {cached_url}")
            return

    # 업로드
    print(f"\n⏳ {service}에 업로드 중...")
    try:
        # 테스트 프로젝트명
        test_project = "test_project"
        url = uploader.upload(test_image, project_name=test_project)
        print(f"\n✅ 업로드 성공!")
        print(f"   URL: {url}")

        # 캐시 저장
        cache.set(test_image, url)
        print(f"\n💾 캐시에 저장됨: {cache_file}")

        # URL 길이 확인
        print(f"\n📊 통계:")
        print(f"   URL 길이: {len(url)} 문자")
        print(f"   예상 토큰: ~{len(url) // 4} 토큰")

        # Base64와 비교
        import base64
        with open(test_image, "rb") as f:
            base64_data = base64.b64encode(f.read()).decode("utf-8")
        base64_url = f"data:image/jpeg;base64,{base64_data}"

        print(f"\n🔍 Base64 비교:")
        print(f"   Base64 길이: {len(base64_url):,} 문자")
        print(f"   Base64 토큰: ~{len(base64_url) // 4:,} 토큰")
        print(f"   절감율: {(1 - len(url) / len(base64_url)) * 100:.2f}%")

    except Exception as e:
        print(f"\n❌ 업로드 실패: {e}")


def main():
    """메인 함수."""
    print("\n이미지 업로드 서비스를 선택하세요:")
    print("1. Imgur (권장 - 간단)")
    print("2. GitHub (영구 보관)")
    print("3. Cloudinary (이미지 최적화)")
    print()

    choice = input("선택 (1-3, 기본: 1): ").strip()

    service_map = {
        "1": "imgur",
        "2": "github",
        "3": "cloudinary",
        "": "imgur",  # 기본값
    }

    service = service_map.get(choice, "imgur")
    test_upload(service)


if __name__ == "__main__":
    main()

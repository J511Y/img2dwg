# 이미지 URL 사용 가이드

파인튜닝 데이터셋에서 이미지를 base64 대신 공개 URL로 사용하는 방법을 설명합니다.

## 🎯 왜 이미지 URL을 사용하나요?

### Base64 방식의 문제점

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..." 
          }
        }
      ]
    }
  ]
}
```

**문제**:
- 1MB 이미지 → 약 **1.3MB base64** → 약 **300k+ 토큰**
- 대부분의 토큰이 이미지에 소비됨
- JSON 데이터는 불과 수천~수만 토큰

### URL 방식의 장점

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "image_url",
          "image_url": {
            "url": "https://i.imgur.com/abc123.jpg"
          }
        }
      ]
    }
  ]
}
```

**장점**:
- URL 자체는 **10~20 토큰**만 소비
- **99% 이상 토큰 절감** (이미지 부분)
- 파인튜닝 비용 대폭 감소
- 업로드 속도 향상

## 📊 토큰 비교

| 항목 | Base64 | URL | 절감율 |
|------|--------|-----|--------|
| 이미지 (1MB) | ~300,000 토큰 | ~15 토큰 | **99.995%** |
| JSON 데이터 | 10,000 토큰 | 10,000 토큰 | 0% |
| **총합** | **310,000 토큰** | **10,015 토큰** | **96.8%** |

## 🚀 사용 방법

### 1. 이미지 서비스 선택

#### 옵션 1: Imgur (추천 - 가장 간단)

**장점**:
- 무료 API
- 간단한 설정
- 안정적인 호스팅
- 별도 저장소 불필요

**단점**:
- 일일 업로드 제한 (1,250개)
- 이미지 크기 제한 (20MB)

**설정**:
1. [Imgur API](https://api.imgur.com/oauth2/addclient) 접속
2. "OAuth 2 authorization without a callback URL" 선택
3. Client ID 발급받기
4. 환경변수 설정:
   ```bash
   # Windows (PowerShell)
   $env:IMGUR_CLIENT_ID="your_client_id_here"
   
   # Linux/Mac
   export IMGUR_CLIENT_ID="your_client_id_here"
   ```

#### 옵션 2: GitHub

**장점**:
- 완전 무료
- 버전 관리
- 영구 보관

**단점**:
- 저장소 필요
- 파일 크기 제한 (100MB)
- 공개 저장소만 가능

**설정**:
1. GitHub에서 공개 저장소 생성 (예: `img2dwg-images`)
2. [Personal Access Token](https://github.com/settings/tokens) 생성
   - `repo` 권한 필요
3. 환경변수 설정:
   ```bash
   # Windows (PowerShell)
   $env:GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
   $env:GITHUB_REPO_OWNER="your-username"
   $env:GITHUB_REPO_NAME="img2dwg-images"
   
   # Linux/Mac
   export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
   export GITHUB_REPO_OWNER="your-username"
   export GITHUB_REPO_NAME="img2dwg-images"
   ```

#### 옵션 3: Cloudinary

**장점**:
- 이미지 최적화 자동
- CDN 제공
- 무료 티어 (25GB)

**단점**:
- 회원가입 필요
- 설정 복잡

**설정**:
1. [Cloudinary](https://cloudinary.com/) 가입
2. Dashboard에서 API credentials 확인
3. 환경변수 설정:
   ```bash
   # Windows (PowerShell)
   $env:CLOUDINARY_URL="cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
   
   # Linux/Mac
   export CLOUDINARY_URL="cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
   ```
4. 패키지 설치:
   ```bash
   uv add cloudinary
   ```

### 2. 데이터셋 생성 (URL 모드)

```bash
# Imgur 사용 (기본)
python scripts/generate_dataset.py \
  --input-data datas \
  --input-json output/json \
  --output output \
  --use-image-url \
  --image-service imgur

# GitHub 사용
python scripts/generate_dataset.py \
  --use-image-url \
  --image-service github

# Cloudinary 사용
python scripts/generate_dataset.py \
  --use-image-url \
  --image-service cloudinary
```

### 3. 캐시 활용

이미지 URL은 자동으로 캐시됩니다:
- 캐시 파일: `output/image_url_cache.json`
- 동일 이미지 재업로드 방지
- 업로드 속도 향상

캐시 예시:
```json
{
  "C:\\Users\\Ace\\Desktop\\개발\\img2dwg\\datas\\project1\\변경전-모형.jpg": "https://i.imgur.com/abc123.jpg",
  "C:\\Users\\Ace\\Desktop\\개발\\img2dwg\\datas\\project1\\변경후-모형.jpg": "https://i.imgur.com/def456.jpg"
}
```

## 🔧 고급 사용법

### 환경변수 파일 (.env)

`.env` 파일 생성 (프로젝트 루트):
```bash
# Imgur
IMGUR_CLIENT_ID=your_client_id_here

# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=img2dwg-images
GITHUB_BRANCH=main

# Cloudinary
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

`.env` 파일 로드 (Python):
```python
from dotenv import load_dotenv
load_dotenv()
```

### 수동 업로드

```python
from pathlib import Path
from img2dwg.utils.image_uploader import ImageUploader, URLCache

# 업로더 초기화
uploader = ImageUploader(service="github")

# 이미지 업로드 (프로젝트명 포함)
image_path = Path("datas/project1/변경전-모형.jpg")
project_name = "project1"
url = uploader.upload(image_path, project_name=project_name)
print(f"업로드 완료: {url}")
# 결과: https://raw.githubusercontent.com/user/repo/main/images/project1/변경전-모형.jpg

# 캐시 사용
cache = URLCache(Path("output/image_url_cache.json"))
cache.set(image_path, url)

# 캐시에서 가져오기
cached_url = cache.get(image_path)
```

**프로젝트명 포함 이유**:
- 여러 프로젝트에서 동일한 파일명 사용 (예: `변경전-모형.jpg`)
- 프로젝트별로 폴더 구조 생성하여 충돌 방지
- GitHub: `images/{프로젝트명}/{파일명}`
- Cloudinary: `img2dwg/{프로젝트명}/{파일명}`

## ⚠️ 주의사항

### 1. API 제한

**Imgur**:
- 시간당 500 요청
- 일일 12,500 요청
- 월간 500,000 요청

**GitHub**:
- 시간당 5,000 요청 (인증 시)
- 파일 크기: 100MB 이하

**Cloudinary**:
- 무료: 월 25 credits
- 1 credit = 1,000 transformations

### 2. 이미지 공개

- 모든 업로드된 이미지는 **공개**됩니다
- 민감한 정보가 포함된 이미지는 주의
- 필요시 이미지 전처리로 민감 정보 제거

### 3. 영구성

**Imgur**:
- 무료 계정: 6개월 미접속 시 삭제 가능
- 계정 등록 권장

**GitHub**:
- 저장소 삭제 전까지 영구 보관
- 가장 안정적

**Cloudinary**:
- 무료 티어: 영구 보관
- 용량 초과 시 추가 비용

## 📈 성능 비교

### 업로드 시간

| 이미지 수 | Base64 | Imgur | GitHub | Cloudinary |
|-----------|--------|-------|--------|------------|
| 10개 | 즉시 | ~30초 | ~60초 | ~45초 |
| 100개 | 즉시 | ~5분 | ~10분 | ~7분 |
| 1000개 | 즉시 | ~50분 | ~100분 | ~70분 |

**참고**: 
- Base64는 업로드 불필요 (인코딩만)
- 하지만 토큰 수가 100배 이상 많음
- 파인튜닝 비용이 훨씬 높음

### 파인튜닝 비용 비교

**예시**: 1,000개 이미지 (각 1MB)

| 방식 | 총 토큰 | 비용 (GPT-4o) |
|------|---------|---------------|
| Base64 | ~310M 토큰 | $3,100 |
| URL | ~10M 토큰 | $100 |
| **절감** | **300M 토큰** | **$3,000** |

**결론**: URL 방식이 **30배 저렴**

## 🎯 권장 설정

### 소규모 프로젝트 (< 100 이미지)
```bash
python scripts/generate_dataset.py \
  --use-image-url \
  --image-service imgur
```

### 중규모 프로젝트 (100~1000 이미지)
```bash
python scripts/generate_dataset.py \
  --use-image-url \
  --image-service github
```

### 대규모 프로젝트 (> 1000 이미지)
```bash
python scripts/generate_dataset.py \
  --use-image-url \
  --image-service cloudinary
```

## 🔍 문제 해결

### Imgur 업로드 실패

```
RuntimeError: Imgur 업로드 실패: 403
```

**해결**:
1. Client ID 확인
2. 일일 제한 확인
3. 이미지 크기 확인 (< 20MB)

### GitHub 업로드 실패

```
RuntimeError: GitHub 업로드 실패: 422
{"message":"Invalid request.\n\n\"sha\" wasn't supplied."}
```

**원인**: 동일한 파일명이 이미 존재하는 경우

**해결**: 자동으로 처리됩니다 (기존 파일 SHA 확인 후 업데이트)

```
RuntimeError: GitHub 업로드 실패: 404
```

**해결**:
1. 저장소 존재 확인
2. Token 권한 확인 (`repo`)
3. 저장소가 공개인지 확인

### Cloudinary 업로드 실패

```
RuntimeError: cloudinary 패키지가 필요합니다
```

**해결**:
```bash
uv add cloudinary
```

## 📚 참고 자료

- [Imgur API 문서](https://apidocs.imgur.com/)
- [GitHub API 문서](https://docs.github.com/en/rest)
- [Cloudinary 문서](https://cloudinary.com/documentation)
- [OpenAI Vision API](https://platform.openai.com/docs/guides/vision)

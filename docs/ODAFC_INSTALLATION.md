# ODA File Converter 설치 가이드

DWG 파일을 처리하기 위해서는 **ODA File Converter**가 필요합니다.

## 📥 다운로드

공식 사이트에서 다운로드:
👉 https://www.opendesign.com/guestfiles/oda_file_converter

## 💻 설치 방법

### Windows

1. **다운로드**
   - Windows 버전 (32-bit 또는 64-bit) 다운로드
   - 예: `ODAFileConverter_24.9.0_Winx64_vc17dll.exe`

2. **설치**
   - 다운로드한 `.exe` 파일 실행
   - 설치 마법사를 따라 진행
   - 기본 설치 경로: `C:\Program Files\ODA\ODAFileConverter\`

3. **설정 파일 생성**
   
   **홈 디렉토리**(`C:\Users\<사용자명>\`)에 `.ezdxfrc` 파일을 생성하고 다음 내용을 추가합니다:
   
   ```ini
   [odafc-addon]
   win_exec_path = "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe"
   ```
   
   **중요 사항**:
   - 파일 위치는 **홈 디렉토리**여야 합니다 (프로젝트 루트 아님)
   - 백슬래시는 **이중으로 이스케이프** (`\\`) 해야 합니다
   - 실제 ODAFileConverter 설치 경로를 확인하세요

4. **설치 확인**
   ```powershell
   # 프로젝트 디렉토리에서 실행
   uv run python examples/test_odafc.py
   ```

### Linux

1. **다운로드**
   - Linux 버전 (DEB 또는 RPM) 다운로드

2. **설치 (DEB)**
   ```bash
   sudo dpkg -i ODAFileConverter_QT5_lnxX64_8.3dll_23.9.deb
   ```

3. **설치 (RPM)**
   ```bash
   sudo rpm -i ODAFileConverter_QT5_lnxX64_8.3dll_23.9.rpm
   ```

4. **GUI 억제 (xvfb 설치)**
   ```bash
   sudo apt-get install xvfb  # Ubuntu/Debian
   sudo yum install xorg-x11-server-Xvfb  # CentOS/RHEL
   ```

5. **설정 파일**
   - `~/.ezdxfrc` 파일 생성:
   ```ini
   [odafc-addon]
   unix_exec_path = "/usr/bin/ODAFileConverter"
   ```

### macOS

1. **다운로드**
   - macOS 버전 다운로드
   - 예: `ODAFileConverter_24.9.0_MacOS.dmg`

2. **설치**
   - DMG 파일을 마운트하고 애플리케이션 폴더로 드래그

3. **명령줄 도구 설정**
   - 터미널에서 실행 가능하도록 심볼릭 링크 생성:
   ```bash
   sudo ln -s "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter" /usr/local/bin/ODAFileConverter
   ```

4. **설정 파일**
   - `~/.ezdxfrc` 파일 생성:
   ```ini
   [odafc-addon]
   unix_exec_path = "/usr/local/bin/ODAFileConverter"
   ```

## ✅ 설치 확인

Python에서 설치 여부 확인:

```python
from ezdxf.addons import odafc

if odafc.is_installed():
    print("✓ ODA File Converter가 설치되어 있습니다.")
else:
    print("✗ ODA File Converter가 설치되어 있지 않습니다.")
```

또는 터미널에서:

```bash
# Windows
ODAFileConverter.exe

# Linux/macOS
ODAFileConverter
```

## 🔧 문제 해결

### "ODAFileConverter를 찾을 수 없습니다"

**원인**: 실행 파일이 PATH에 없거나 설정 파일이 잘못됨

**해결방법**:
1. 설치 경로 확인
2. `.ezdxfrc` 파일에 절대 경로 설정
3. 환경 변수 `PATH`에 설치 경로 추가

### GUI가 나타남 (Linux)

**원인**: xvfb가 설치되지 않음

**해결방법**:
```bash
sudo apt-get install xvfb
```

### 변환이 실패함

**원인**: DWG 파일이 손상되었거나 지원하지 않는 버전

**해결방법**:
1. DWG 파일을 AutoCAD에서 열어 확인
2. 최신 버전의 ODA File Converter 설치
3. DWG 파일을 DXF로 수동 변환 후 사용

## 📝 참고

- ODA File Converter는 무료로 사용 가능합니다
- 상업적 용도로도 사용 가능합니다
- DWG 파일의 모든 버전을 지원합니다 (R12 ~ 최신)
- GUI 버전과 CLI 버전이 모두 제공됩니다

## 🔗 추가 자료

- [ODA 공식 사이트](https://www.opendesign.com/)
- [ezdxf ODA File Converter 문서](https://ezdxf.readthedocs.io/en/stable/addons/odafc.html)

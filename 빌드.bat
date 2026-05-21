@echo off
chcp 65001 >nul
REM ============================================================
REM  DIA_MC (게임패드 지원본) 원클릭 빌드 스크립트  - Windows 전용
REM  이 파일을 dia_mc.py 와 같은 폴더에 두고 더블클릭하세요.
REM  결과물: dist\DIA_MC\dia_mc.exe
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/4] Python 확인...
where python >nul 2>nul
if errorlevel 1 (
    echo  [오류] Python 이 설치되어 있지 않습니다.
    echo         https://www.python.org/downloads/ 에서 Python 3.12 를 설치한 뒤
    echo         설치 시 "Add Python to PATH" 를 체크하세요.
    pause
    exit /b 1
)
python --version

echo.
echo [2/4] 필요한 패키지 설치 (pynput / pygame / pyinstaller)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo  [오류] 패키지 설치 실패. 인터넷 연결을 확인하세요.
    pause
    exit /b 1
)

echo.
echo [3/4] exe 빌드 중... (시간이 좀 걸립니다)
python -m PyInstaller --noconfirm dia_mc.spec
if errorlevel 1 (
    echo  [오류] 빌드 실패.
    pause
    exit /b 1
)

echo.
echo [4/4] 로고/예시 파일 복사...
copy /Y dia_logo.ico "dist\DIA_MC\" >nul
copy /Y dia_logo.png "dist\DIA_MC\" >nul
copy /Y "예시참고매크로.json" "dist\DIA_MC\" >nul

echo.
echo ============================================================
echo  완료!  실행 파일 위치:  dist\DIA_MC\dia_mc.exe
echo  dist\DIA_MC 폴더 전체를 옮겨서 사용/배포하면 됩니다.
echo ============================================================
echo.
echo  실행 파일 폴더를 엽니다...
explorer "dist\DIA_MC"
pause

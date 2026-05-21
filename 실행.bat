@echo off
chcp 65001 >nul
REM ============================================================
REM  DIA_MC (게임패드 지원본) - 빌드 없이 바로 실행
REM  스마트 앱 컨트롤(Smart App Control)이 exe 를 막는 경우,
REM  신뢰된 python.exe 로 dia_mc.py 를 직접 실행하면 차단되지 않습니다.
REM  이 파일을 dia_mc.py 와 같은 폴더에 두고 더블클릭하세요.
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/2] Python 확인...
where python >nul 2>nul
if errorlevel 1 (
    echo  [오류] Python 이 설치되어 있지 않습니다.
    echo         https://www.python.org/downloads/ 에서 Python 3.12 설치 후
    echo         설치 화면에서 "Add Python to PATH" 를 꼭 체크하세요.
    pause
    exit /b 1
)
python --version

echo.
echo [2/2] 필요한 패키지 확인/설치 (pynput) 후 실행...
python -m pip install -r requirements.txt
echo.
echo  실행합니다. 이 검은 창은 닫지 마세요 (닫으면 매크로도 종료됩니다).
echo.
python dia_mc.py
if errorlevel 1 (
    echo.
    echo  [알림] 위에 오류 메시지가 있으면 그대로 캡처해서 알려주세요.
    pause
)

@echo off
cd /d "%~dp0"
echo.
echo [1/3] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo  [ERROR] Python is not installed. Get Python 3.12 from python.org
    echo          and check "Add Python to PATH" during setup.
    pause
    exit /b 1
)
python --version
echo.
echo [2/3] Installing packages (pynput / pyinstaller)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo  [ERROR] Package install failed. Check your internet connection.
    pause
    exit /b 1
)
echo.
echo [3/3] Building single exe...
python -m PyInstaller --noconfirm dia_mc.spec
if errorlevel 1 (
    echo  [ERROR] Build failed.
    pause
    exit /b 1
)
echo.
echo  DONE. Single executable: dist\dia_mc.exe
echo  Just double-click dist\dia_mc.exe to run. No other files needed.
explorer "dist"
pause

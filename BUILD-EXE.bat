@echo off
cd /d "%~dp0"
echo.
echo [1/4] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo  [ERROR] Python is not installed. Get Python 3.12 from python.org
    echo          and check "Add Python to PATH" during setup.
    pause
    exit /b 1
)
python --version
echo.
echo [2/4] Installing packages (pynput / pyinstaller)...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 (
    echo  [ERROR] Package install failed. Check your internet connection.
    pause
    exit /b 1
)
echo.
echo [3/4] Building exe...
python -m PyInstaller --noconfirm dia_mc.spec
if errorlevel 1 (
    echo  [ERROR] Build failed.
    pause
    exit /b 1
)
echo.
echo [4/4] Copying logo/example files...
copy /Y dia_logo.ico "dist\DIA_MC\" >nul
copy /Y dia_logo.png "dist\DIA_MC\" >nul
copy /Y *.json "dist\DIA_MC\" >nul
echo.
echo  DONE. Executable: dist\DIA_MC\dia_mc.exe
explorer "dist\DIA_MC"
pause

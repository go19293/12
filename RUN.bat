@echo off
cd /d "%~dp0"
echo.
echo [1/2] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    echo  [ERROR] Python is not installed.
    echo          Install Python 3.12 from https://www.python.org/downloads/
    echo          and check "Add Python to PATH" during setup, then retry.
    pause
    exit /b 1
)
python --version
echo.
echo [2/2] Installing pynput (if needed) and starting...
python -m pip install -r requirements.txt
echo.
echo  Starting DIA_MC. Keep this black window OPEN (closing it stops the macro).
echo.
python dia_mc.py
echo.
echo  [NOTE] If an error appeared above, please screenshot it.
pause

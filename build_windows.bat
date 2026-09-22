@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" was not found. Install 64-bit Python 3.11 or newer.
  pause
  exit /b 1
)

if not exist ".venv-build\Scripts\python.exe" py -m venv .venv-build
if errorlevel 1 goto :error

call ".venv-build\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
python -m PyInstaller --noconfirm --clean PNGWhiteConverter.spec
if errorlevel 1 goto :error

echo.
echo Build complete: dist\WhiteShift.exe
echo Double-click the EXE to start the app.
pause
endlocal
exit /b 0

:error
echo.
echo Build failed. Check the messages above.
pause
endlocal
exit /b 1

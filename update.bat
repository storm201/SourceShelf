@echo off
REM SourceShelf - local updater for Windows.
REM   double-click this file, or run:  update.bat --quick
REM Set a token for a much bigger API budget:  set GITHUB_TOKEN=ghp_xxx
cd /d "%~dp0"
chcp 65001 >nul 2>nul

where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo Python 3 is required: https://www.python.org/downloads/
  echo During install, tick "Add Python to PATH".
  pause
  exit /b 1
)

%PY% scripts\update.py %*
echo.
pause

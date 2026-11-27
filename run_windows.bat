@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_windows.ps1"
if errorlevel 1 (
  echo.
  echo Setup or launch failed. Read the error above.
  pause
)

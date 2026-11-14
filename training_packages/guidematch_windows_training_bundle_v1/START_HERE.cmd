@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_training.ps1"
set EXIT_CODE=%ERRORLEVEL%
echo.
if not "%EXIT_CODE%"=="0" (
  echo Training stopped with exit code %EXIT_CODE%.
) else (
  echo Training completed. See outputs\summary.md
)
pause
exit /b %EXIT_CODE%

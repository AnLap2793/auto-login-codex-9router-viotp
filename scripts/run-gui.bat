@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\pythonw.exe" (
    py -3.11 -m venv .venv || goto :error
)

.venv\Scripts\python.exe -m pip install -e . || goto :error
start "" .venv\Scripts\pythonw.exe -m login_codex_9router.gui
exit /b 0

:error
echo Khong the khoi dong. Hay chay build.bat de cai dat day du.
pause
exit /b 1

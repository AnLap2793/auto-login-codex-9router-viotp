@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv || goto :error
)

.venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
.venv\Scripts\python.exe -m pip install -e . || goto :error
.venv\Scripts\python.exe -m compileall src tests || goto :error
.venv\Scripts\python.exe -m unittest discover -s tests -v || goto :error
.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name login-codex-9router --collect-all playwright scripts\gui_entry.py || goto :error

echo.
echo Build thanh cong: dist\login-codex-9router.exe
exit /b 0

:error
echo.
echo Build that bai.
exit /b 1

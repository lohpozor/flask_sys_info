@echo off
rem Run Carv Sys with waitress (production server for Windows).
rem Keep this file ASCII-only: cmd.exe misreads UTF-8 Cyrillic in .bat files.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment .venv not found.
    echo     Create it:        python -m venv .venv
    echo     Install packages: .venv\Scripts\python -m pip install -r requirements.txt
    pause
    exit /b 1
)

set PORT=5002
echo Carv Sys: http://localhost:%PORT%
echo Stop the server: Ctrl+C
rem Open the browser after ~2 seconds so the server has time to start
start "" /b cmd /c "ping -n 3 127.0.0.1 > nul & start http://localhost:%PORT%"
".venv\Scripts\python.exe" -m waitress --listen=127.0.0.1:%PORT% app:app
pause

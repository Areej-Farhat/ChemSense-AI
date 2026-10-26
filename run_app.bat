@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\streamlit.exe" (
    echo ChemSense AI is not set up yet.
    echo.
    echo Double-clicking this file works AFTER you finish the first-time setup in README.md.
    echo.
    pause
    exit /b 1
)

echo Starting ChemSense AI...
echo A browser window should open. Keep this window open while you use the app.
echo Close this window or press Ctrl+C to stop the app.
echo.
".venv\Scripts\streamlit.exe" run app.py
pause

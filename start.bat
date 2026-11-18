@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo LCE-Tool wird gestartet ...
python -c "import streamlit" 2>nul
if errorlevel 1 (
  echo.
  echo Streamlit ist nicht installiert. Bitte einmal ausfuehren:
  echo     pip install -r requirements.txt
  echo.
  pause
  exit /b 1
)
start "" cmd /c "timeout /t 4 >nul & start http://localhost:8501"
python -m streamlit run app.py --server.port 8501
echo.
echo Das Tool wurde beendet. Falls oben eine Fehlermeldung steht, bitte lesen.
pause

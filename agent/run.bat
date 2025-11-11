@echo off
echo Starting Simplified Voice Agent...
echo.

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo.
)

call venv\Scripts\activate.bat

echo Server starting on http://localhost:8084
echo Open your browser and go to http://localhost:8084
echo Press Ctrl+C to stop
echo.
python simple_voice_agent.py

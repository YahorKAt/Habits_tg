@echo off
cd bot

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

echo Installing requirements...
pip install -r requirements.txt >nul

REM --- Load .env variables automatically ---
for /f "tokens=1,2 delims==" %%a in (..\ .env) do set %%a=%%b

echo Starting Telegram bot...
python example_bot.py

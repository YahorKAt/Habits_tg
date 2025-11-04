@echo off
cd backend

REM --- Create virtual environment if not exists ---
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate

REM --- Install dependencies ---
echo Installing requirements...
pip install -r requirements.txt

REM --- Set environment variables for DEV mode ---
set DEV_MODE=true
set DEV_USER_ID=1
REM Optional: set BOT_TOKEN if needed for production testing
REM set BOT_TOKEN=your_token_here

REM --- Load .env and run migrations ---
echo Migrating database...
python migrate_db.py

REM --- Start backend ---
echo Starting FastAPI server in DEV mode...
echo DEV_MODE=%DEV_MODE%
echo DEV_USER_ID=%DEV_USER_ID%
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

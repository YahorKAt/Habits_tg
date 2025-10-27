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
pip install -r requirements.txt >nul

REM --- Load .env and run migrations ---
echo Migrating database...
python migrate_db.py

REM --- Start backend ---
echo Starting FastAPI server...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

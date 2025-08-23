@echo off
echo Setting up environment variables...
set DEV_MODE=true
set DEV_USER_ID=1
set BOT_TOKEN=8294461897:AAGmR53gKOlz1-O8c-1aDRh6prSoLIrS0TQ

echo Starting backend server...
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

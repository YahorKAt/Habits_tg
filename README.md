# Habits Telegram Mini App

Full-stack Telegram Mini App for tasks & subtasks with stats.

## Quick Start (Windows)

### 1. Backend
```bash
# Option 1: Use batch file (recommended)
run_backend.bat

# Option 2: Manual setup
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set DEV_MODE=true
set DEV_USER_ID=1
set BOT_TOKEN=8294461897:AAGmR53gKOlz1-O8c-1aDRh6prSoLIrS0TQ
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend
npm i
npm run dev
```

### 3. Expose with localtunnel
```bash
# New terminal for backend
lt --port 8000

# New terminal for frontend  
lt --port 5173
```

### 4. Bot
```bash
# Option 1: Use batch file (recommended)
run_bot.bat

# Option 2: Manual setup
cd bot
pip install -r requirements.txt
set BOT_TOKEN=8294461897:AAGmR53gKOlz1-O8c-1aDRh6prSoLIrS0TQ
set WEBAPP_URL=https://floppy-chefs-yawn.loca.lt
python example_bot.py
```

## Environment Variables

- `DEV_MODE=true`: Enables development mode (skips strict auth)
- `DEV_USER_ID=1`: User ID for development mode
- `BOT_TOKEN`: Your Telegram bot token
- `WEBAPP_URL`: URL where your frontend is hosted

## Notes
- Uses Telegram WebApp API for auth via `X-Telegram-Init-Data` header
- Designed to work inside Telegram client WebView
- Backend runs on port 8000, frontend on port 5173




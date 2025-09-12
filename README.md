# Habits Telegram Mini App

Full-stack Telegram Mini App for tasks & subtasks with stats and recurring tasks support.

## Features

- ✅ **Tasks & Subtasks Management** - Create, complete, and delete tasks with subtasks
- ✅ **Recurring Tasks** - Set daily, weekly, monthly, or custom schedules
- ✅ **Dedicated Creation Page** - Full-featured form for task creation with all options
- ✅ **Statistics** - Track completion rates for 7 days, 30 days, or all time
- ✅ **Telegram WebApp Integration** - Native Telegram client experience
- ✅ **Responsive UI** - Modern interface with Tailwind CSS

## Interface Structure

### Main Page (Tasks)
- List of all tasks with completion status
- Button "Добавить задачу" to open creation page
- Quick subtask addition to existing tasks

### Task Creation Page
- **Task Title** - Required field for task name
- **Repeat Type** - NONE, DAILY, WEEKLY, MONTHLY, CUSTOM
- **Interval** - Every N days/weeks/months
- **Custom Date** - Specific date/time for custom schedule
- **End Date** - Optional end date for recurring tasks
- **Subtasks** - Add multiple subtasks before creating
- **Navigation** - Back button and Create button

### Statistics Page
- Completion rates for different time periods
- Visual representation of progress

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

### 2. Database Migration (if updating existing database)
```bash
cd backend
python migrate_db.py
```

### 3. Frontend
```bash
cd frontend
npm i
npm run dev
```

### 4. Expose with localtunnel
```bash
# New terminal for backend
lt --port 8000

# New terminal for frontend  
lt --port 5173
```

### 5. Bot
```bash
# Option 1: Use batch file (recommended)
run_bot.bat

# Option 2: Manual setup
cd bot
pip install -r requirements.txt
set BOT_TOKEN=8294461897:AAGmR53gKOlz1-O8c-1aDRh6prSoLIrS0TQ
set WEBAPP_URL=https://cuddly-clocks-play.loca.lt
python example_bot.py
```

## New Features: Recurring Tasks

### Task Types
- **NONE** - One-time task
- **DAILY** - Every N days
- **WEEKLY** - Every N weeks  
- **MONTHLY** - Every N months
- **CUSTOM** - Specific date/time

### How It Works
1. Click "Добавить задачу" button
2. Fill in task title and select repeat type
3. Set interval (every 1, 2, 3... days/weeks/months)
4. Optionally set end date
5. Add subtasks if needed
6. Click "Создать задачу"
7. When completed, next due date is automatically calculated
8. Tasks can be completed multiple times

## Environment Variables

- `DEV_MODE=true`: Enables development mode (skips strict auth)
- `DEV_USER_ID=1`: User ID for development mode
- `BOT_TOKEN`: Your Telegram bot token
- `WEBAPP_URL`: URL where your frontend is hosted

## Notes
- Uses Telegram WebApp API for auth via `X-Telegram-Init-Data` header
- Designed to work inside Telegram client WebView
- Backend runs on port 8000, frontend on port 5173
- SQLite database with automatic migration support
- Clean separation between task list and creation interface
- Enum values use uppercase (NONE, DAILY, WEEKLY, MONTHLY, CUSTOM)




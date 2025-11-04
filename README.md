# Habits Telegram Mini App

Full-stack Telegram Mini App for habit tracking with modern UI design, statistics, and journal features.

## Features

- ✅ **Modern UI Design** - Clean, intuitive interface matching Telegram design guidelines
- ✅ **Habit Tracking** - Create and track daily, weekly, and monthly habits
- ✅ **Statistics Dashboard** - Visual charts and progress tracking with calendar view
- ✅ **Journal System** - Daily notes and reflections with calendar navigation
- ✅ **Category System** - Organize habits by Sport, Study, Work, and Personal
- ✅ **Streak Tracking** - Visual streak indicators and completion rates
- ✅ **Telegram WebApp Integration** - Native Telegram client experience
- ✅ **Responsive Design** - Optimized for mobile devices

## Interface Structure

### Tasks Page
- **Filter Tabs** - All, Active, Completed tasks
- **Habit Cards** - Each habit shows category, frequency, and streak
- **Floating Action Button** - Quick access to create new habits
- **Category Icons** - Visual indicators for Sport 🏆, Study 🎓, Work 💼, Personal 👤

### Create Task Page
- **Task Title** - Required field for habit name
- **Description** - Optional detailed description
- **Category Selection** - Visual category cards with icons
- **Frequency Options** - Daily, Weekly, Monthly with descriptions
- **Preview Section** - Shows how the habit will look
- **Modern Form Design** - Clean, intuitive interface

### Statistics Page
- **Activity Chart** - Pie chart showing completion rates
- **Schedule Calendar** - Weekly view with completion indicators
- **Summary Cards** - Completion percentage and streak days
- **Habit Streaks** - Visual dot indicators for each habit

### Journal Page
- **Monthly Calendar** - Navigate between months
- **Daily Notes** - Add and view notes for specific dates
- **Mood Selection** - Choose from 12 different mood emojis
- **Time Stamps** - Each note shows creation time
- **Mood Display** - Visual mood indicators for each note

### Habit Categories
- **Sport** 🏆 - Physical activities and fitness
- **Study** 🎓 - Learning and education
- **Work** 💼 - Professional tasks and projects
- **Personal** 👤 - Personal development and self-care

### Frequency Options
- **Daily** - Every day habit tracking
- **Weekly** - Weekly habit completion
- **Monthly** - Monthly goal achievement

### How It Works
1. Navigate to Tasks page
2. Click floating "+" button to create new habit
3. Fill in habit title and optional description
4. Select category with visual cards
5. Choose frequency (daily/weekly/monthly)
6. Preview your habit before creating
7. Track completion and view streaks
8. Monitor progress in Statistics page
9. Add daily reflections in Journal page

### UI Components
- **Modern Cards** - Clean, rounded design with shadows
- **Visual Categories** - Icon-based category selection
- **Streak Indicators** - Dot-based streak visualization
- **Charts** - Pie charts for completion statistics
- **Calendar Views** - Monthly and weekly calendar navigation
- **Bottom Navigation** - Easy switching between main sections

## Environment Variables

### Backend
- `DEV_MODE=true`: Enables development mode (skips strict auth)
- `DEV_USER_ID=1`: User ID for development mode
- `BOT_TOKEN`: Your Telegram bot token
- `WEBAPP_URL`: URL where your frontend is hosted

### Frontend
- `VITE_API_URL`: URL бэкенд API (по умолчанию в DEV режиме используется `http://localhost:8000`)

**Для локальной разработки:**
1. Создайте файл `frontend/.env` с содержимым:
   ```
   VITE_API_URL=http://localhost:8000
   ```
2. Или просто используйте дефолтное значение - в DEV режиме автоматически используется `http://localhost:8000`

## Notes
- Uses Telegram WebApp API for auth via `X-Telegram-Init-Data` header
- Designed to work inside Telegram client WebView
- Backend runs on port 8000, frontend on port 5173
- SQLite database with automatic migration support
- Clean separation between task list and creation interface
- Enum values use uppercase (NONE, DAILY, WEEKLY, MONTHLY, CUSTOM)





### Quick Start (Windows)

### 1. Backend
```bash
# Option 1: Use batch file (recommended)
run_backend.bat

# Option 2: Manual setup
cd backend
python -m venv .venv && .venv\\Scripts\\activate
pip install -r requirements.txt
set DEV_MODE=true
set DEV_USER_ID=1
set BOT_TOKEN=8294461897:AAEdrDJDWFPylUnv3P-dN60ImlQf1vrtr6A
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Database Migration (if updating existing database)
```bash
cd backend
python migrate_db.py
```

**Проверка подключения к БД:**
После запуска бэкенда проверьте:
```bash
# Проверка общего здоровья API
curl http://localhost:8000/health

# Проверка подключения к БД
curl http://localhost:8000/health/db

# Полная диагностика (импорты, переменные окружения)
curl http://localhost:8000/health/full
```

**Устранение ошибки 503:**
Если получаете 503 ошибку, проверьте:
1. ✅ Бэкенд запущен (проверьте консоль на ошибки)
2. ✅ Все зависимости установлены: `pip install -r requirements.txt`
3. ✅ База данных доступна (проверьте `/health/db`)
4. ✅ DEV_MODE установлен (проверьте `/health/full`)

Также проверьте логи бэкенда на наличие ошибок импорта или подключения к БД.

### 3. Frontend

**Локальная разработка (DEV режим):**

```bash
cd frontend
npm i
npm run dev
```

**Особенности DEV режима:**
- Автоматически использует `http://localhost:8000` как API URL (если не указан `VITE_API_URL`)
- Работает без Telegram WebApp (можно разрабатывать в браузере)
- Использует мок-данные для `initData` если Telegram недоступен
- Все запросы идут на локальный бэкенд

### 4. Expose with localtunnel
```bash

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
set BOT_TOKEN=8294461897:AAEdrDJDWFPylUnv3P-dN60ImlQf1vrtr6A
set WEBAPP_URL=https://every-adults-occur.loca.lt
python example_bot.py
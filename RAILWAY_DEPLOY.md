# Деплой на Railway

## Шаг 1: Создать два сервиса на Railway

### Сервис 1: Backend (FastAPI)

1. Зайдите на [railway.app](https://railway.app) и создайте новый проект
2. Подключите GitHub репозиторий
3. Создайте **первый сервис** для Backend:
   - Root Directory: `/` (корень проекта)
   - Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - В настройках добавьте **Environment Variables**:
     ```
     BOT_TOKEN=ваш_токен_от_BotFather
     DATABASE_URL=будет_автоматически_после_добавления_PostgreSQL
     ```

4. Добавьте **PostgreSQL** к Backend сервису:
   - Нажмите "New" → "Database" → "Add PostgreSQL"
   - Railway автоматически добавит `DATABASE_URL` в переменные окружения

5. Настройте **Public Domain**:
   - В настройках сервиса нажмите "Settings" → "Networking" → "Generate Domain"
   - Получите URL типа `https://your-backend.up.railway.app`

### Сервис 2: Bot (Telegram Bot)

1. В том же проекте создайте **второй сервис** для Bot:
   - Нажмите "New" → "GitHub Repo" (выберите тот же репозиторий)
   - Root Directory: `/` (корень проекта)
   - Start Command: `python bot/example_bot.py`
   - В настройках добавьте **Environment Variables**:
     ```
     BOT_TOKEN=ваш_токен_от_BotFather
     API_BASE_URL=https://your-backend.up.railway.app
     ```

2. Настройте **Service Type**:
   - В Settings → "Service" выберите **Worker** (не Web)

## Шаг 2: Обновить Frontend (Vercel)

В настройках Vercel обновите переменную окружения:
```
VITE_API_URL=https://your-backend.up.railway.app
```

Перезапустите деплой на Vercel.

## Шаг 3: Обновить CORS на Backend

Убедитесь что в `backend/app/main.py` добавлен домен Railway в CORS:

```python
origins = [
    "https://habits-tg.vercel.app",
    "https://*.railway.app",
    "https://*.telegram.org",
    "https://t.me",
]
```

## Шаг 4: Проверка

1. Откройте бота в Telegram
2. Нажмите "Открыть приложение"
3. Попробуйте создать задачу
4. Проверьте логи на Railway:
   - Backend сервис: должны быть логи авторизации
   - Bot сервис: должен быть запущен без ошибок

## Переменные окружения

### Backend Service:
- `BOT_TOKEN` - токен бота от @BotFather
- `DATABASE_URL` - автоматически от PostgreSQL
- `PORT` - автоматически от Railway

### Bot Service:
- `BOT_TOKEN` - токен бота от @BotFather
- `API_BASE_URL` - URL вашего backend на Railway

## Команды для локальной разработки

```bash
# Запуск backend локально
cd backend
uvicorn app.main:app --reload

# Запуск bot локально
cd bot
python example_bot.py
```

## Troubleshooting

### Ошибка "Terminated by other getupdates"
- Убедитесь что бот запущен только в **одном месте**
- Остановите все локальные экземпляры бота
- Проверьте что на Railway запущен только один сервис бота

### Ошибка 401 Unauthorized
- Проверьте что `BOT_TOKEN` одинаковый на Backend и Bot сервисах
- Проверьте логи на Railway Backend для деталей

### База данных не работает
- Убедитесь что PostgreSQL добавлен к Backend сервису
- Проверьте что `DATABASE_URL` присутствует в переменных окружения


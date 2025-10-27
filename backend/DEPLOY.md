# Инструкция по развертыванию на Render

## Настройка переменных окружения

В панели Render добавьте следующие переменные окружения:

### Обязательные переменные:
- `BOT_TOKEN` - Токен вашего Telegram бота (получите у @BotFather)
- `DEV_MODE` - Режим разработки (поставьте `false` для production)

### Опциональные переменные:
- `DEV_USER_ID` - ID пользователя для dev режима (только если DEV_MODE=true)

## Шаги для деплоя:

1. **Подключите ваш GitHub репозиторий** к Render

2. **Создайте Web Service** в Render:
   - Name: `habits-backend` (или любое другое имя)
   - Environment: `Python 3`
   - Build Command: 
     ```bash
     pip install -r backend/requirements.txt
     ```
   - Start Command:
     ```bash
     cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

3. **Настройте переменные окружения** в Render Dashboard

4. **После первого деплоя запустите миграцию**:
   ```bash
   python backend/migrate_db.py
   ```
   (Это можно сделать через терминал Render или создав отдельный task)

## Проверка работы:

1. Откройте URL вашего backend (например: `https://habits-tg.onrender.com/`)
2. Должен вернуться JSON: `{"status": "ok", "message": "Backend running"}`

## Возможные проблемы:

### Ошибка 401 Unauthorized
- Проверьте, что переменная `BOT_TOKEN` установлена корректно
- Убедитесь, что frontend отправляет заголовок `X-Telegram-Init-Data`
- Проверьте логи в Render для получения детальной информации об ошибке

### Проблемы с CORS
- Убедитесь, что в `backend/app/main.py` указан правильный origin для frontend
- Проверьте, что заголовок `X-Telegram-Init-Data` включен в список allowed headers

### База данных
- База данных SQLite создается автоматически при первом запуске
- Для production рекомендуется использовать PostgreSQL
- Запустите миграцию после добавления новых полей в модели


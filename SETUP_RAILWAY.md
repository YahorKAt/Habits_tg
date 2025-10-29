# Быстрая настройка Railway

## ✅ Что уже готово:

1. ✅ `nixpacks.toml` - конфигурация для Backend
2. ✅ `bot/nixpacks.toml` - конфигурация для Bot
3. ✅ `Procfile` - альтернативная конфигурация
4. ✅ `psycopg2-binary` добавлен в `backend/requirements.txt`
5. ✅ `database.py` поддерживает PostgreSQL
6. ✅ CORS настроен для Railway

## 🚀 Шаги для деплоя:

### 1. Создайте проект на Railway

1. Зайдите на https://railway.app
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите ваш репозиторий

### 2. Настройте Backend сервис

1. После создания проекта, Railway создаст первый сервис
2. Переименуйте его в "backend"
3. В Settings:
   - **Root Directory**: `backend` (ВАЖНО!)
   - **Start Command**: оставьте пустым (будет использован из nixpacks.toml)

4. Добавьте PostgreSQL:
   - Нажмите "New" → "Database" → "Add PostgreSQL"
   - Railway автоматически создаст и подключит базу данных

5. Добавьте переменные окружения (Variables):
   ```
   BOT_TOKEN=ваш_токен_от_BotFather
   ```
   (DATABASE_URL добавится автоматически после подключения PostgreSQL)

6. Включите публичный домен:
   - Settings → Networking → "Generate Domain"
   - Скопируйте URL (например: `https://backend-production-xxxx.up.railway.app`)

### 3. Создайте Bot сервис

1. В том же проекте нажмите "New" → "GitHub Repo"
2. Выберите тот же репозиторий
3. Переименуйте сервис в "bot"
4. В Settings:
   - **Root Directory**: `bot` (ВАЖНО!)
   - **Start Command**: оставьте пустым (будет использован из nixpacks.toml)

5. Добавьте переменные окружения:
   ```
   BOT_TOKEN=ваш_токен_от_BotFather
   WEBAPP_URL=https://habits-tg.vercel.app
   ```

### 4. Обновите Frontend на Vercel

1. Зайдите в настройки вашего проекта на Vercel
2. Перейдите в Settings → Environment Variables
3. Обновите или добавьте:
   ```
   VITE_API_URL=https://ваш-backend-url.up.railway.app
   ```
4. Перезапустите деплой (Deployments → последний деплой → Redeploy)

### 5. Проверьте работу

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Нажмите кнопку "Open Habits Mini App"
4. Попробуйте создать задачу

### 6. Проверьте логи

В Railway для каждого сервиса:
- Нажмите на сервис
- Перейдите во вкладку "Deployments"
- Нажмите "View Logs"

**Backend логи должны показывать:**
```
INFO: Starting init_data validation
INFO: Telegram Auth Debug
INFO: ✅ Hash matched!
INFO: Successfully authenticated user_id: 342751730
```

**Bot логи должны показывать:**
```
Using bot token: 8294461897...
WebApp URL: https://habits-tg.vercel.app
Starting bot...
```

## 🐛 Troubleshooting

### "Terminated by other getupdates"
- **Проблема**: Бот запущен в нескольких местах одновременно
- **Решение**: Остановите все другие экземпляры (локальные, Render, и т.д.)

### 401 Unauthorized
- **Проблема**: Hash не совпадает
- **Решение**: 
  1. Проверьте что `BOT_TOKEN` одинаковый на Backend и Bot
  2. Убедитесь что нет лишних пробелов в токене
  3. Проверьте логи Backend на Railway

### База данных не работает
- **Проблема**: DATABASE_URL не установлен или неверный
- **Решение**:
  1. Убедитесь что PostgreSQL подключен к Backend сервису
  2. Проверьте что переменная `DATABASE_URL` присутствует
  3. Перезапустите Backend сервис

### CORS ошибки
- **Проблема**: Frontend не может подключиться к Backend
- **Решение**:
  1. Убедитесь что домен Railway добавлен в CORS (уже сделано)
  2. Проверьте что `VITE_API_URL` на Vercel правильный
  3. Перезапустите деплой на Vercel

## 📝 Важные заметки

- PostgreSQL на Railway **бесплатный**, но есть лимиты
- Логи на Railway доступны только последние 5000 строк
- Bot сервис должен быть типа "Worker", а не "Web"
- Backend сервис должен быть типа "Web" с публичным доменом

## 🔑 Переменные окружения

### Backend Service:
```
BOT_TOKEN=ваш_токен
DATABASE_URL=автоматически_от_PostgreSQL
PORT=автоматически
```

### Bot Service:
```
BOT_TOKEN=ваш_токен
WEBAPP_URL=https://habits-tg.vercel.app
```

### Frontend (Vercel):
```
VITE_API_URL=https://ваш-backend.up.railway.app
```

## ✨ Готово!

Теперь у вас полностью развернутое приложение:
- 🤖 Bot на Railway
- 🔧 Backend на Railway с PostgreSQL
- 🎨 Frontend на Vercel


from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from .database import init_db, get_db
from .schemas import TaskCreate, SubtaskCreate, SubtaskUpdate, NoteCreate
from . import crud
import logging
from sqlalchemy.orm import Session
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone


from .telegram_auth import parse_and_validate_init_data

def get_client_time(header_client_time: str = Header(None, alias="X-Client-Time")) -> datetime:
    """
    Получает локальное время клиента из заголовка запроса и конвертирует в UTC.
    Клиент отправляет локальное время в ISO формате с timezone offset (например: 2024-11-09T10:30:00.000+03:00).
    Если заголовок не передан, используем UTC.
    """
    if header_client_time:
        try:
            # Парсим ISO формат времени от клиента (локальное время с timezone offset)
            client_time = datetime.fromisoformat(header_client_time.replace('Z', '+00:00'))
            
            # Если время имеет timezone, конвертируем в UTC
            if client_time.tzinfo:
                # Конвертируем локальное время клиента в UTC
                client_time_utc = client_time.astimezone(timezone.utc)
                # Возвращаем как naive datetime в UTC (для совместимости с остальным кодом)
                return client_time_utc.replace(tzinfo=None)
            # Если timezone нет, считаем что это уже UTC
            return client_time
        except (ValueError, AttributeError) as e:
            logger.debug(f"Не удалось распарсить время клиента: {e}")
            pass
    # Если заголовок не передан или невалидный - используем UTC
    return datetime.now(timezone.utc)

def get_client_timezone(header_client_time: str = Header(None, alias="X-Client-Time")):
    """
    Получает timezone offset клиента из заголовка запроса.
    Возвращает timezone объект или None если не удалось определить.
    """
    if header_client_time:
        try:
            client_time = datetime.fromisoformat(header_client_time.replace('Z', '+00:00'))
            if client_time.tzinfo:
                return client_time.tzinfo
        except (ValueError, AttributeError):
            pass
    return None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Отключаем лишние логи от uvicorn и других библиотек
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)
logging.getLogger('apscheduler.executors').setLevel(logging.WARNING)
logging.getLogger('apscheduler.jobstores').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Создаем планировщик задач
scheduler = BackgroundScheduler()


app = FastAPI(title="Habits Mini App API")

origins = [
    "https://habits-tg.vercel.app",  # ваш домен Vercel
    "backend-production-cd9a.up.railway.app",  # Railway
    "https://*.telegram.org",
    "https://t.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class TimezoneMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматического сохранения часового пояса пользователя"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Сохраняем часовой пояс только для аутентифицированных запросов
        if "X-Telegram-Init-Data" in request.headers:
            try:
                user = parse_and_validate_init_data(request.headers.get("X-Telegram-Init-Data"))
                if user and "id" in user:
                    user_id = int(user["id"])
                    client_time_header = request.headers.get("X-Client-Time")
                    
                    if client_time_header:
                        try:
                            client_time = datetime.fromisoformat(client_time_header.replace('Z', '+00:00'))
                            if client_time.tzinfo:
                                # Извлекаем offset в формате "+03:00"
                                offset = client_time.strftime("%z")
                                if offset:
                                    # Форматируем как "+03:00"
                                    offset_formatted = f"{offset[:3]}:{offset[3:]}"
                                    db = next(get_db())
                                    try:
                                        crud.update_user_timezone(db, user_id, offset_formatted)
                                    except Exception as e:
                                        logger.debug(f"Не удалось сохранить часовой пояс для пользователя {user_id}: {e}")
                                    finally:
                                        db.close()
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Не удалось распарсить время клиента: {e}")
            except Exception as e:
                logger.debug(f"Не удалось сохранить часовой пояс: {e}")
        
        return response

app.add_middleware(TimezoneMiddleware)



def generate_tasks_job():
    """Задача для генерации задач - запускается каждый час и проверяет, для каких пользователей наступило 00:00"""
    try:
        db = next(get_db())
        from datetime import timedelta
        
        # Получаем текущее время в UTC
        now_utc = datetime.now(timezone.utc)
        current_hour_utc = now_utc.hour
        
        # Получаем всех пользователей с сохраненным часовым поясом
        users = crud.get_all_users_with_timezone(db)
        
        # Также получаем пользователей без часового пояса (используем UTC по умолчанию)
        from sqlalchemy import select
        from . import models
        users_without_tz = db.execute(
            select(models.Task.user_id).distinct()
        ).scalars().all()
        
        # Создаем словарь для быстрого доступа
        users_dict = {user.user_id: user for user in users}
        
        # Добавляем пользователей без часового пояса (используем UTC)
        for user_id in users_without_tz:
            if user_id not in users_dict:
                # Создаем временный объект User с UTC
                from types import SimpleNamespace
                temp_user = SimpleNamespace(user_id=user_id, timezone_offset="+00:00")
                users.append(temp_user)
                users_dict[user_id] = temp_user
        
        if not users:
            logger.debug("Пользователи не найдены")
            db.close()
            return
        
        total_created = 0
        
        for user in users:
            if not user.timezone_offset:
                continue
            
            try:
                # Парсим offset (например, "+03:00" -> timedelta(hours=3))
                offset_str = user.timezone_offset
                sign = 1 if offset_str[0] == '+' else -1
                hours = int(offset_str[1:3])
                minutes = int(offset_str[4:6]) if len(offset_str) > 4 else 0
                offset_hours = sign * (hours + minutes / 60)
                
                # Вычисляем текущий час в часовом поясе пользователя
                user_tz = timezone(timedelta(hours=offset_hours))
                now_user_tz = now_utc.astimezone(user_tz)
                user_hour = now_user_tz.hour
                
                # Если в часовом поясе пользователя наступило 00:00
                if user_hour == 0:
                    # Вычисляем начало нового дня пользователя в его часовом поясе
                    user_day_start = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
                    user_day_start_utc = user_day_start.astimezone(timezone.utc)
                    
                    # Важно: user_day_start_utc может быть предыдущим днем в UTC (например, 21:00 предыдущего дня)
                    # Но это правильная дата для генерации задач - она представляет начало нового дня в часовом поясе пользователя
                    # Передаем is_user_timezone_start=True, чтобы функция использовала дату как есть
                    # Задачи будут созданы с created_at = user_day_start_utc (начало дня в часовом поясе пользователя, в UTC)
                    count = crud.generate_daily_tasks(db, user_day_start_utc, user_id=user.user_id, is_user_timezone_start=True)
                    total_created += count
                    if count > 0:
                        logger.info(f"✅ Создано {count} задач для пользователя {user.user_id} (часовой пояс {user.timezone_offset})")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка генерации задач для пользователя {user.user_id}: {e}")
                continue
        
        if total_created > 0:
            logger.info(f"📋 Всего создано {total_created} задач для {len(users)} пользователей")
        else:
            logger.debug(f"⏭️  Задачи не созданы (проверено {len(users)} пользователей)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в задаче генерации задач: {e}")
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    try:
        logger.info("🚀 Запуск приложения...")
        init_db()
        
        # Настраиваем планировщик для генерации задач каждый час
        # Он проверит всех пользователей и создаст задачи для тех, у кого наступило 00:00 в их часовом поясе
        scheduler.add_job(
            generate_tasks_job,
            trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
            id='generate_daily_tasks',
            name='Генерация ежедневных задач в полночь для каждого пользователя',
            replace_existing=True
        )
        scheduler.start()
        logger.info("✅ Планировщик запущен - задачи создаются в 00:00 по локальному времени каждого пользователя")
        logger.info("✅ Приложение успешно запущено")
    except Exception as e:
        logger.error(f"❌ Не удалось запустить приложение: {e}")
        raise


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Останавливаем планировщик при выключении приложения"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Планировщик остановлен")


def get_user_id(x_telegram_init_data: str | None = Header(default=None)) -> int:
    if not x_telegram_init_data:
        logger.debug("Отсутствует заголовок X-Telegram-Init-Data")
        raise HTTPException(status_code=401, detail="Missing Telegram init data")
    
    user = parse_and_validate_init_data(x_telegram_init_data)
    if not user or "id" not in user:
        logger.warning("Не удалось валидировать Telegram auth данные")
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    
    user_id = int(user["id"])
    logger.debug(f"Пользователь аутентифицирован: user_id={user_id}")
    return user_id


@app.get("/health")
def health() -> JSONResponse:
    """Базовая проверка работоспособности API"""
    return JSONResponse({
        "status": "ok",
        "message": "API is running"
    })


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> JSONResponse:
    """Проверка подключения к базе данных"""
    try:
        # Простой запрос для проверки подключения
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.commit()
        return JSONResponse({
            "status": "ok",
            "database": "connected"
        })
    except Exception as e:
        logger.error(f"Ошибка проверки базы данных: {e}")
        return JSONResponse({
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }, status_code=500)


@app.get("/health/full")
def health_full() -> JSONResponse:
    """Полная диагностика системы"""
    import sys
    diagnostics = {
        "status": "ok",
        "python_version": sys.version,
        "dev_mode": os.getenv("DEV_MODE", "not set"),
        "dev_user_id": os.getenv("DEV_USER_ID", "not set"),
        "bot_token_set": "yes" if os.getenv("BOT_TOKEN") else "no",
        "database_url": os.getenv("DATABASE_URL", "using default"),
    }
    
    # Проверка импортов
    try:
        from telegram_webapp_auth.data import WebAppChat
        diagnostics["telegram_webapp_auth"] = "imported"
    except ImportError as e:
        diagnostics["telegram_webapp_auth"] = f"import failed: {str(e)}"
    
    try:
        from sqlalchemy import create_engine
        diagnostics["sqlalchemy"] = "imported"
    except ImportError as e:
        diagnostics["sqlalchemy"] = f"import failed: {str(e)}"
    
    return JSONResponse(diagnostics)


@app.post("/migrate")
def run_migrations_endpoint(db: Session = Depends(get_db)) -> JSONResponse:
    """Ручной запуск миграций базы данных"""
    try:
        from . import migrations
        migrations.migrate_all(db)
        return JSONResponse({
            "status": "ok",
            "message": "Migrations applied successfully"
        })
    except Exception as e:
        logger.error(f"Ошибка миграции: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@app.post("/task")
def add_task(payload: TaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    try:
        task = crud.create_task(
            db, 
            user_id=user_id, 
            title=payload.title,
            description=payload.description,
            repeat_interval=payload.repeat_interval,
            next_due_date=payload.next_due_date,
            end_date=payload.end_date,
            category=payload.category,
            frequency=payload.frequency
        )
        logger.debug(f"Создана задача: id={task.id}, title={payload.title[:30]}")
        return task
    except Exception as e:
        logger.error(f"Ошибка создания задачи: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@app.put("/task/{task_id}")
def update_task(
    task_id: int, 
    payload: TaskCreate, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_user_id),
    client_time: datetime = Depends(get_client_time)
):
    try:
        task = crud.update_task(
            db, 
            task_id=task_id,
            user_id=user_id, 
            title=payload.title,
            description=payload.description,
            repeat_interval=payload.repeat_interval,
            next_due_date=payload.next_due_date,
            end_date=payload.end_date,
            category=payload.category,
            frequency=payload.frequency,
            current_time=client_time
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/subtask")
def add_subtask(payload: SubtaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    task = crud.get_task(db, task_id=payload.task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    subtask = crud.create_subtask(db, task_id=payload.task_id, user_id=user_id, title=payload.title)
    return subtask


@app.delete("/subtask/{subtask_id}")
def delete_subtask(subtask_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_subtask(db, subtask_id=subtask_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return {"ok": True}


@app.post("/subtask/{subtask_id}/complete")
def complete_subtask(subtask_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    # Получаем текущее состояние подзадачи через временный запрос
    from sqlalchemy import select
    from . import models
    subtask = db.execute(select(models.Subtask).where(models.Subtask.id == subtask_id)).scalar_one_or_none()
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    # Проверяем, что подзадача принадлежит пользователю
    parent_task = crud.get_task(db, task_id=subtask.task_id, user_id=user_id)
    if not parent_task:
        raise HTTPException(status_code=404, detail="Subtask not found")
    # Переключаем состояние (toggle)
    new_completed_state = not subtask.completed
    subtask = crud.set_subtask_completed(db, subtask_id=subtask_id, user_id=user_id, completed=new_completed_state)
    return subtask



@app.delete("/task/{task_id}")
def delete_task(
    task_id: int, 
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_user_id),
    client_time: datetime = Depends(get_client_time)
):
    try:
        deleted = crud.delete_task(db, task_id=task_id, user_id=user_id, current_time=client_time)
        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tasks")
def list_tasks(
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_user_id),
    date: str = None,  # Опциональный параметр для выбранной даты (YYYY-MM-DD)
    client_time: datetime = Depends(get_client_time),
    header_client_time: str = Header(None, alias="X-Client-Time")
):
    try:
        selected_date = None
        if date:
            try:
                from datetime import datetime, timezone, timedelta
                # Парсим дату как локальное время клиента (начало дня)
                # Клиент выбирает дату в своем локальном времени (например, 9 ноября)
                # Нужно конвертировать начало и конец этого дня в UTC для фильтрации
                local_date = datetime.strptime(date, "%Y-%m-%d")
                
                # Определяем timezone клиента из заголовка
                client_tz = None
                if header_client_time:
                    try:
                        client_time_with_tz = datetime.fromisoformat(header_client_time.replace('Z', '+00:00'))
                        if client_time_with_tz.tzinfo:
                            client_tz = client_time_with_tz.tzinfo
                    except (ValueError, AttributeError):
                        pass
                
                # Если удалось определить timezone клиента, используем его
                if client_tz:
                    # Создаем начало дня в локальном времени клиента
                    local_day_start = local_date.replace(tzinfo=client_tz)
                    # Конвертируем в UTC
                    selected_date = local_day_start.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    # Если timezone не определен, считаем что дата уже в UTC
                    selected_date = local_date.replace(tzinfo=timezone.utc)
            except ValueError:
                pass  # Игнорируем неверный формат даты
        
        return crud.list_tasks_with_subtasks(db, user_id=user_id, selected_date=selected_date, current_time=client_time)
    except Exception as e:
        logger.error(f"Ошибка получения списка задач: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")




@app.post("/tasks/generate-today")
def generate_today_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """
    Ручной запуск генерации задач для сегодняшнего дня.
    Используется для тестирования.
    """
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = crud.generate_daily_tasks(db, today)
        logger.info(f"Ручная генерация: создано {count} задач за {today.date()}")
        return {
            "ok": True,
            "date": today.isoformat(),
            "tasks_created": count,
            "message": f"Created {count} tasks for {today.date()}"
        }
    except Exception as e:
        logger.error(f"Ошибка ручной генерации задач: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate tasks: {str(e)}")


@app.post("/task/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    try:
        # Получаем задачу чтобы узнать текущее состояние
        task = crud.get_task(db, task_id=task_id, user_id=user_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        # Переключаем состояние (toggle)
        new_completed_state = not task.completed
        task = crud.set_task_completed(db, task_id=task_id, user_id=user_id, completed=new_completed_state)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/subtask/{subtask_id}")
def update_subtask(subtask_id: int, payload: SubtaskUpdate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    subtask = crud.update_subtask(db, subtask_id=subtask_id, user_id=user_id, title=payload.title)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask


@app.get("/habits")
def habits_stats(db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    from . import habits_stats
    return habits_stats.get_habits_stats(db, user_id=user_id)


@app.get("/stats")
def stats(period: str, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    if period not in {"day", "week", "month", "all"}:
        raise HTTPException(status_code=400, detail="Invalid period. Must be: day, week, month, or all")
    return crud.get_stats(db, user_id=user_id, period=period)


@app.post("/notes")
def add_note(payload: NoteCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    note = crud.create_note(
        db, 
        user_id=user_id, 
        content=payload.content,
        date=payload.date,
        mood=payload.mood
    )
    return note


@app.get("/notes")
def list_notes(
    date: str = None, 
    year: int = None, 
    month: int = None,
    db: Session = Depends(get_db), 
    user_id: int = Depends(get_user_id)
):
    # Если указан год и месяц - возвращаем все заметки за месяц
    if year is not None and month is not None:
        notes_dict = crud.get_notes_by_month(db, user_id=user_id, year=year, month=month)
        # Преобразуем словарь в список для совместимости
        return list(notes_dict.values())
    
    # Иначе возвращаем заметки за конкретную дату
    if date:
        return crud.get_notes_by_date(db, user_id=user_id, date=date)
    
    return []


@app.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_note(db, note_id=note_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}




from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from .database import init_db, get_db
from .schemas import TaskCreate, SubtaskCreate, SubtaskUpdate, NoteCreate
from . import crud
import logging
from sqlalchemy.orm import Session
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime


from .telegram_auth import parse_and_validate_init_data

def get_client_time(header_client_time: str = Header(None, alias="X-Client-Time")) -> datetime:
    """
    Получает время клиента из заголовка запроса.
    Если заголовок не передан, использует локальное время сервера.
    """
    if header_client_time:
        try:
            # Парсим ISO формат времени от клиента
            client_time = datetime.fromisoformat(header_client_time.replace('Z', '+00:00'))
            # Преобразуем в локальное время (убираем timezone)
            if client_time.tzinfo:
                # Конвертируем UTC в локальное время сервера
                client_time = client_time.replace(tzinfo=None)
            return client_time
        except (ValueError, AttributeError):
            pass
    # Если заголовок не передан или невалидный - используем время сервера
    return datetime.now()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
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



def generate_tasks_job():
    """Задача для генерации задач в 00:00 каждый день"""
    try:
        db = next(get_db())
        # В 00:00 создаем задачи для нового дня (сегодня) на основе задач предыдущего дня
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = crud.generate_daily_tasks(db, today)
        logger.info(f"🔄 Scheduled task: Generated {count} tasks for {today.date()}")
    except Exception as e:
        logger.error(f"❌ Error in scheduled task generation: {e}", exc_info=True)
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    try:
        logger.info("🚀 Starting up application...")
        init_db()
        
        # Настраиваем планировщик для генерации задач в 00:00 локального времени каждый день
        # Используем None для timezone, чтобы использовалось локальное время сервера
        scheduler.add_job(
            generate_tasks_job,
            trigger=CronTrigger(hour=0, minute=0, timezone=None),  # Локальное время сервера
            id='generate_daily_tasks',
            name='Generate daily tasks at midnight',
            replace_existing=True
        )
        scheduler.start()
        logger.info("✅ Scheduler started - tasks will be generated at 00:00 local time daily")
        logger.info("✅ Application started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Останавливаем планировщик при выключении приложения"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ Scheduler stopped")


def get_user_id(x_telegram_init_data: str | None = Header(default=None)) -> int:
    if not x_telegram_init_data:
        logger.warning("Missing X-Telegram-Init-Data header")
        raise HTTPException(status_code=401, detail="Missing Telegram init data")
    
    logger.info(f"Received X-Telegram-Init-Data header, length: {len(x_telegram_init_data) if x_telegram_init_data else 0}")
    
    user = parse_and_validate_init_data(x_telegram_init_data)
    if not user or "id" not in user:
        logger.error(f"Failed to validate init_data. Header present: {bool(x_telegram_init_data)}")
        logger.error(f"Header length: {len(x_telegram_init_data) if x_telegram_init_data else 0}")
        logger.error(f"BOT_TOKEN from env: {'SET' if os.getenv('BOT_TOKEN') else 'NOT SET'}")
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    
    user_id = int(user["id"])
    logger.info(f"Successfully authenticated user_id: {user_id}")
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
        logger.error(f"Database health check failed: {e}", exc_info=True)
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
        logger.error(f"Migration failed: {e}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@app.post("/task")
def add_task(payload: TaskCreate, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    try:
        logger.info(f"Creating task: title={payload.title}, category={payload.category}, frequency={payload.frequency}")
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
        logger.info(f"Task created successfully with id={task.id}")
        return task
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
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
    subtask = crud.create_subtask(db, task_id=payload.task_id, title=payload.title)
    return subtask


@app.delete("/subtask/{subtask_id}")
def delete_subtask(subtask_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_subtask(db, subtask_id=subtask_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return {"ok": True}


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
    date: str = None  # Опциональный параметр для выбранной даты (YYYY-MM-DD)
):
    try:
        selected_date = None
        if date:
            try:
                from datetime import datetime
                selected_date = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                pass  # Игнорируем неверный формат даты
        
        return crud.list_tasks_with_subtasks(db, user_id=user_id, selected_date=selected_date)
    except Exception as e:
        logger.error(f"Error in list_tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")




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
def list_notes(date: str, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    return crud.get_notes_by_date(db, user_id=user_id, date=date)


@app.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_user_id)):
    deleted = crud.delete_note(db, note_id=note_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"ok": True}




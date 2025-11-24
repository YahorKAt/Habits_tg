"""
Главный файл FastAPI приложения
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone, timedelta
import logging
import os
from types import SimpleNamespace

from .database import init_db, get_db
from .middleware.timezone_middleware import TimezoneMiddleware
from .routes import health, tasks, notes, stats
from .repositories.user_repository import UserRepository
from .services.scheduler_service import SchedulerService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Отключаем лишние логи
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('apscheduler.scheduler').setLevel(logging.WARNING)
logging.getLogger('apscheduler.executors').setLevel(logging.WARNING)
logging.getLogger('apscheduler.jobstores').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Создаем планировщик задач
scheduler = BackgroundScheduler()

# Создаем приложение
app = FastAPI(title="Habits Mini App API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Добавляем middleware для часовых поясов
app.add_middleware(TimezoneMiddleware)

# Подключаем роутеры
app.include_router(health.router, tags=["health"])
app.include_router(tasks.router, tags=["tasks"])
app.include_router(notes.router, tags=["notes"])
app.include_router(stats.router, tags=["stats"])


def generate_tasks_job():
    """Задача для генерации задач - запускается каждый час и проверяет, для каких пользователей наступило 00:00"""
    try:
        db = next(get_db())
        
        # Получаем текущее время в UTC
        now_utc = datetime.now(timezone.utc)
        current_hour_utc = now_utc.hour
        
        # Получаем всех пользователей с сохраненным часовым поясом
        users = UserRepository.get_all_with_timezone(db)
        
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
                temp_user = SimpleNamespace(user_id=user_id, timezone_offset="+00:00")
                users.append(temp_user)
                users_dict[user_id] = temp_user
        
        if not users:
            logger.info("ℹ️  Пользователи не найдены для генерации задач")
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
                    
                    count = SchedulerService.generate_daily_tasks(
                        db,
                        user_day_start_utc,
                        user_id=user.user_id,
                        is_user_timezone_start=True
                    )
                    total_created += count
                    if count > 0:
                        logger.info(f"✅ Создано {count} задач для пользователя {user.user_id} (часовой пояс {user.timezone_offset}, локальное время: {now_user_tz.strftime('%H:%M')})")
                    else:
                        logger.debug(f"⏭️  Задачи не созданы для пользователя {user.user_id} (локальное время: {now_user_tz.strftime('%H:%M')}, не 00:00)")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка генерации задач для пользователя {user.user_id}: {e}")
                continue
        
        if total_created > 0:
            logger.info(f"✅ Всего создано {total_created} задач для {len(users)} пользователей")
        else:
            logger.info(f"ℹ️  Задачи не созданы (проверено {len(users)} пользователей)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в задаче генерации задач: {e}")
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    """Инициализация приложения при запуске"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Начало запуска FastAPI приложения...")
        logger.info("=" * 60)
        
        logger.info("📊 Инициализация базы данных...")
        init_db()
        logger.info("✅ База данных инициализирована")
        
        logger.info("⏰ Настройка планировщика задач...")
        # Настраиваем планировщик для генерации задач каждый час
        scheduler.add_job(
            generate_tasks_job,
            trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
            id='generate_daily_tasks',
            name='Генерация ежедневных задач в полночь для каждого пользователя',
            replace_existing=True
        )
        scheduler.start()
        logger.info("✅ Планировщик запущен - задачи создаются в 00:00 по локальному времени каждого пользователя")
        logger.info("=" * 60)
        logger.info("✅ Приложение успешно запущено и готово к работе")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске приложения: {e}", exc_info=True)
        raise


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Остановка приложения при выключении"""
    logger.info("=" * 60)
    logger.info("🛑 Начало остановки приложения...")
    logger.info("=" * 60)
    if scheduler.running:
        logger.info("⏹️  Остановка планировщика задач...")
        scheduler.shutdown()
        logger.info("✅ Планировщик остановлен")
    else:
        logger.info("ℹ️  Планировщик уже был остановлен")
    logger.info("✅ Приложение успешно остановлено")

"""Утилиты для работы с базой данных в боте"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Optional
from types import SimpleNamespace

logger = logging.getLogger(__name__)

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    logger.info(f"📦 DATABASE_URL found in environment variables")
    # Логируем только начало URL для безопасности (скрываем пароль)
    url_preview = DATABASE_URL.split('@')[0] + '@' + DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else DATABASE_URL[:50]
    logger.info(f"📦 DATABASE_URL preview: {url_preview}...")
else:
    logger.warning("⚠️ DATABASE_URL not found in environment variables, will use SQLite")

# Railway/Heroku используют postgres://, но SQLAlchemy требует postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("✅ Fixed DATABASE_URL for PostgreSQL (postgres:// -> postgresql://)")

# Проверяем, является ли это внутренним Railway URL
if DATABASE_URL and "railway.internal" in DATABASE_URL:
    logger.info("✅ Using Railway internal database URL (works within Railway network)")
elif DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    logger.info("✅ Using PostgreSQL database URL")

# Если DATABASE_URL не установлен, используем SQLite (для локальной разработки)
if not DATABASE_URL:
    # Пытаемся найти базу данных в разных местах
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(bot_dir)
    backend_dir = os.path.join(project_root, "backend")
    
    # Проверяем несколько возможных путей
    possible_paths = [
        os.path.join(backend_dir, "habits.db"),  # backend/habits.db
        os.path.join(project_root, "habits.db"),  # корень проекта
        os.path.join(bot_dir, "habits.db"),  # bot/habits.db
    ]
    
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    # Если файл не найден, используем путь по умолчанию
    if not db_path:
        db_path = possible_paths[0]
        logger.warning(f"⚠️ Database file not found, will create at: {db_path}")
    else:
        logger.info(f"✅ Found database file at: {db_path}")
    
    DATABASE_URL = f"sqlite:///{db_path}"

logger.info(f"📦 Using DATABASE_URL: {DATABASE_URL[:50]}..." if len(DATABASE_URL) > 50 else f"📦 Using DATABASE_URL: {DATABASE_URL}")

# Настройки подключения для разных типов БД
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # Убеждаемся, что директория существует
    db_dir = os.path.dirname(DATABASE_URL.replace("sqlite:///", ""))
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"⚠️ Could not create database directory: {e}")

try:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        echo=False,
        pool_pre_ping=True,  # Проверяем соединение перед использованием
    )
    logger.info("✅ Database engine created successfully")
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {e}", exc_info=True)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_all_users_with_timezone() -> List[SimpleNamespace]:
    """Получает всех пользователей с сохраненным часовым поясом"""
    db = SessionLocal()
    try:
        # Проверяем, существует ли таблица users
        try:
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
        except Exception as e:
            logger.warning(f"⚠️ Table 'users' might not exist: {e}")
            # Если таблицы нет, возвращаем пустой список
            return []
        
        # Получаем пользователей с часовым поясом
        result = db.execute(
            text("SELECT user_id, timezone_offset FROM users WHERE timezone_offset IS NOT NULL")
        )
        users = []
        for row in result:
            users.append(SimpleNamespace(user_id=row[0], timezone_offset=row[1]))
        
        logger.debug(f"Found {len(users)} users with timezone")
        
        # Также получаем пользователей без часового пояса из задач (используем UTC)
        try:
            result_tasks = db.execute(
                text("SELECT DISTINCT user_id FROM tasks")
            )
            user_ids_with_tasks = {row[0] for row in result_tasks}
            
            # Добавляем пользователей без часового пояса
            existing_user_ids = {user.user_id for user in users}
            for user_id in user_ids_with_tasks:
                if user_id not in existing_user_ids:
                    users.append(SimpleNamespace(user_id=user_id, timezone_offset="+00:00"))
            
            logger.debug(f"Total users after adding from tasks: {len(users)}")
        except Exception as e:
            logger.warning(f"⚠️ Could not get users from tasks table: {e}")
        
        return users
    except Exception as e:
        logger.error(f"❌ Error getting users with timezone: {e}", exc_info=True)
        return []
    finally:
        db.close()


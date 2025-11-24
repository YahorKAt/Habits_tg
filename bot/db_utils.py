"""Утилиты для работы с базой данных в боте"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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



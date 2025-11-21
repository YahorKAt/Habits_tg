from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
import logging

logger = logging.getLogger(__name__)

# Определяем путь к БД относительно корня проекта backend
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Путь относительно backend директории
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, "habits.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    logger.debug(f"Используется путь к БД по умолчанию: {db_path}")

logger.debug(f"URL базы данных: {DATABASE_URL[:50]}...")

# Railway/Heroku используют postgres://, но SQLAlchemy требует postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.debug("Исправлен DATABASE_URL для PostgreSQL")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,  # Включить для отладки SQL запросов
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from . import models  # noqa: F401
    try:
        # Создаем таблицы если их нет
        logger.info("🔧 Создание/проверка таблиц базы данных...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы базы данных созданы/проверены")
        
        # Применяем миграции
        logger.info("🔧 Применение миграций базы данных...")
        from . import migrations
        db = SessionLocal()
        try:
            migrations.migrate_all(db)
        except Exception as migration_error:
            logger.error(f"❌ Ошибка при применении миграций: {migration_error}")
            # Не прерываем запуск приложения, но логируем ошибку
            # Попробуем еще раз через несколько секунд
            raise
        finally:
            db.close()
            
        logger.info("✅ База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"❌ Не удалось инициализировать базу данных: {e}")
        raise


def get_db() -> Session:
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        # Тестовое подключение для проверки доступности БД
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()




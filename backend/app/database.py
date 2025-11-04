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
    logger.info(f"Using default database path: {db_path}")

logger.info(f"Database URL: {DATABASE_URL}")

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
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise


def get_db() -> Session:
    """Dependency для получения сессии БД"""
    db = SessionLocal()
    try:
        # Тестовое подключение для проверки доступности БД
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        logger.error(f"Database connection error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()





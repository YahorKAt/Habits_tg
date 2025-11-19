"""Утилиты для работы с базой данных в боте"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from typing import List, Optional
from types import SimpleNamespace

# Получаем DATABASE_URL из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Railway/Heroku используют postgres://, но SQLAlchemy требует postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Если DATABASE_URL не установлен, используем SQLite (для локальной разработки)
if not DATABASE_URL:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(backend_dir, "backend", "habits.db")
    DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_all_users_with_timezone() -> List[SimpleNamespace]:
    """Получает всех пользователей с сохраненным часовым поясом"""
    db = SessionLocal()
    try:
        # Получаем пользователей с часовым поясом
        result = db.execute(
            text("SELECT user_id, timezone_offset FROM users WHERE timezone_offset IS NOT NULL")
        )
        users = []
        for row in result:
            users.append(SimpleNamespace(user_id=row[0], timezone_offset=row[1]))
        
        # Также получаем пользователей без часового пояса из задач (используем UTC)
        result_tasks = db.execute(
            text("SELECT DISTINCT user_id FROM tasks")
        )
        user_ids_with_tasks = {row[0] for row in result_tasks}
        
        # Добавляем пользователей без часового пояса
        existing_user_ids = {user.user_id for user in users}
        for user_id in user_ids_with_tasks:
            if user_id not in existing_user_ids:
                users.append(SimpleNamespace(user_id=user_id, timezone_offset="+00:00"))
        
        return users
    finally:
        db.close()


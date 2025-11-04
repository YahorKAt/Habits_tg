"""
Универсальные миграции для базы данных
Поддерживает SQLite и PostgreSQL
"""
import logging
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .database import engine, SessionLocal

logger = logging.getLogger(__name__)


def column_exists(table_name: str, column_name: str, db: Session) -> bool:
    """Проверяет существование колонки в таблице"""
    try:
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        logger.warning(f"Could not inspect table {table_name}: {e}")
        # Fallback: проверяем через SQL запрос
        try:
            if db.bind.dialect.name == 'sqlite':
                result = db.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in result.fetchall()]
            else:  # PostgreSQL
                result = db.execute(text(
                    f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_name = '{table_name}' AND column_name = '{column_name}'"
                ))
                columns = [row[0] for row in result.fetchall()]
            return column_name in columns
        except Exception as e2:
            logger.error(f"Fallback column check failed: {e2}")
            return False


def migrate_all(db: Session):
    """Применяет все миграции"""
    try:
        # Проверяем, существует ли таблица tasks
        inspector = inspect(db.bind)
        tables = inspector.get_table_names()
        
        if 'tasks' not in tables:
            logger.info("⏭️  Таблица 'tasks' не существует, миграции будут применены при создании таблиц")
            return
        
        # Миграция 1: Добавление поля streak
        if not column_exists('tasks', 'streak', db):
            logger.info("🔄 Миграция 1: Добавление поля 'streak' в таблицу tasks...")
            if db.bind.dialect.name == 'sqlite':
                db.execute(text("ALTER TABLE tasks ADD COLUMN streak INTEGER NOT NULL DEFAULT 0"))
            else:  # PostgreSQL
                db.execute(text("ALTER TABLE tasks ADD COLUMN streak INTEGER NOT NULL DEFAULT 0"))
            logger.info("✅ Поле 'streak' добавлено")
        else:
            logger.info("⏭️  Поле 'streak' уже существует, пропускаем")
        
        # Миграция 2: Добавление полей deleted и deleted_at
        if not column_exists('tasks', 'deleted', db):
            logger.info("🔄 Миграция 2: Добавление полей 'deleted' и 'deleted_at' в таблицу tasks...")
            if db.bind.dialect.name == 'sqlite':
                db.execute(text("ALTER TABLE tasks ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0"))
                db.execute(text("ALTER TABLE tasks ADD COLUMN deleted_at DATETIME"))
            else:  # PostgreSQL
                db.execute(text("ALTER TABLE tasks ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT FALSE"))
                db.execute(text("ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP"))
            logger.info("✅ Поля 'deleted' и 'deleted_at' добавлены")
        else:
            logger.info("⏭️  Поля 'deleted' и 'deleted_at' уже существуют, пропускаем")
        
        db.commit()
        logger.info("✅ Все миграции применены успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при применении миграций: {e}", exc_info=True)
        db.rollback()
        raise


def run_migrations():
    """Запускает миграции"""
    db = SessionLocal()
    try:
        # Сначала создаем таблицы если их нет
        from .models import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Таблицы созданы/проверены")
        
        # Затем применяем миграции
        migrate_all(db)
        
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_migrations()


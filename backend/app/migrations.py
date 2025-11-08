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
        # Используем SQLAlchemy inspector
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        exists = column_name in columns
        logger.debug(f"Column {table_name}.{column_name} exists check: {exists}")
        return exists
    except Exception as e:
        logger.warning(f"Could not inspect table {table_name} using inspector: {e}")
        # Fallback: проверяем через SQL запрос
        try:
            if db.bind.dialect.name == 'sqlite':
                result = db.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in result.fetchall()]
            else:  # PostgreSQL
                result = db.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :table_name AND column_name = :column_name"
                ), {"table_name": table_name, "column_name": column_name})
                columns = [row[0] for row in result.fetchall()]
            exists = len(columns) > 0
            logger.debug(f"Column {table_name}.{column_name} exists check (fallback): {exists}")
            return exists
        except Exception as e2:
            logger.error(f"Fallback column check failed: {e2}")
            # Если не можем проверить, предполагаем что колонка не существует
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
        
        logger.info(f"🔍 Проверка миграций для таблицы 'tasks'...")
        
        # Миграция 1: Добавление поля streak
        if not column_exists('tasks', 'streak', db):
            logger.info("🔄 Миграция 1: Добавление поля 'streak' в таблицу tasks...")
            try:
                if db.bind.dialect.name == 'sqlite':
                    db.execute(text("ALTER TABLE tasks ADD COLUMN streak INTEGER NOT NULL DEFAULT 0"))
                else:  # PostgreSQL
                    db.execute(text("ALTER TABLE tasks ADD COLUMN streak INTEGER NOT NULL DEFAULT 0"))
                db.commit()
                logger.info("✅ Поле 'streak' добавлено")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось добавить поле 'streak' (возможно, уже существует): {e}")
                db.rollback()
                # Проверяем еще раз после ошибки
                if column_exists('tasks', 'streak', db):
                    logger.info("✅ Поле 'streak' существует, продолжаем")
                else:
                    raise
        else:
            logger.info("⏭️  Поле 'streak' уже существует, пропускаем")
        
        # Миграция 2: Добавление полей deleted и deleted_at
        if not column_exists('tasks', 'deleted', db):
            logger.info("🔄 Миграция 2: Добавление полей 'deleted' и 'deleted_at' в таблицу tasks...")
            try:
                if db.bind.dialect.name == 'sqlite':
                    db.execute(text("ALTER TABLE tasks ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0"))
                    db.execute(text("ALTER TABLE tasks ADD COLUMN deleted_at DATETIME"))
                else:  # PostgreSQL
                    db.execute(text("ALTER TABLE tasks ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT FALSE"))
                    db.execute(text("ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP"))
                db.commit()
                logger.info("✅ Поля 'deleted' и 'deleted_at' добавлены")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось добавить поля 'deleted'/'deleted_at' (возможно, уже существуют): {e}")
                db.rollback()
                # Проверяем еще раз после ошибки
                if column_exists('tasks', 'deleted', db) and column_exists('tasks', 'deleted_at', db):
                    logger.info("✅ Поля 'deleted' и 'deleted_at' существуют, продолжаем")
                else:
                    raise
        else:
            logger.info("⏭️  Поля 'deleted' и 'deleted_at' уже существуют, пропускаем")
        
        # Миграция 3: Удаление поля repeat_type (заменено на frequency)
        if column_exists('tasks', 'repeat_type', db):
            logger.info("🔄 Миграция 3: Удаление поля 'repeat_type' из таблицы tasks...")
            try:
                if db.bind.dialect.name == 'sqlite':
                    # SQLite не поддерживает DROP COLUMN напрямую, нужно пересоздать таблицу
                    # Для простоты просто пропускаем удаление в SQLite (поле просто не будет использоваться)
                    logger.warning("⚠️  SQLite не поддерживает DROP COLUMN. Поле 'repeat_type' останется в таблице, но не будет использоваться.")
                else:  # PostgreSQL
                    db.execute(text("ALTER TABLE tasks DROP COLUMN IF EXISTS repeat_type"))
                    db.commit()
                    logger.info("✅ Поле 'repeat_type' удалено")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось удалить поле 'repeat_type': {e}")
                db.rollback()
                # Не прерываем выполнение, поле просто останется неиспользуемым
                logger.info("⚠️  Поле 'repeat_type' останется в таблице, но не будет использоваться")
        else:
            logger.info("⏭️  Поле 'repeat_type' уже удалено, пропускаем")
        
        logger.info("✅ Все миграции проверены и применены успешно")
        
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


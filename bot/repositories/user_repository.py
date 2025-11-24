"""
Репозиторий для работы с пользователями в боте
"""
from typing import List
from types import SimpleNamespace
import logging

from db_utils import SessionLocal
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    @staticmethod
    def get_all_with_timezone() -> List[SimpleNamespace]:
        """Получает всех пользователей с сохраненным часовым поясом"""
        logger.debug("🔍 Начало получения пользователей с часовым поясом из базы данных...")
        db = SessionLocal()
        try:
            # Проверяем, существует ли таблица users
            logger.debug("🔎 Проверка существования таблицы 'users'...")
            try:
                db.execute(text("SELECT 1 FROM users LIMIT 1"))
                logger.debug("✅ Таблица 'users' существует")
            except Exception as e:
                logger.warning(f"⚠️  Таблица 'users' может не существовать: {e}")
                return []
            
            # Получаем пользователей с часовым поясом
            logger.debug("📊 Запрос пользователей с сохраненным часовым поясом...")
            result = db.execute(
                text("SELECT user_id, timezone_offset FROM users WHERE timezone_offset IS NOT NULL")
            )
            users = []
            for row in result:
                users.append(SimpleNamespace(user_id=row[0], timezone_offset=row[1]))
            
            logger.info(f"✅ Найдено {len(users)} пользователей с сохраненным часовым поясом")
            
            # Также получаем пользователей без часового пояса из задач (используем UTC)
            logger.debug("🔍 Поиск пользователей без часового пояса в таблице 'tasks'...")
            try:
                result_tasks = db.execute(
                    text("SELECT DISTINCT user_id FROM tasks")
                )
                user_ids_with_tasks = {row[0] for row in result_tasks}
                logger.debug(f"📋 Найдено {len(user_ids_with_tasks)} уникальных пользователей в таблице 'tasks'")
                
                # Добавляем пользователей без часового пояса
                existing_user_ids = {user.user_id for user in users}
                added_count = 0
                for user_id in user_ids_with_tasks:
                    if user_id not in existing_user_ids:
                        users.append(SimpleNamespace(user_id=user_id, timezone_offset="+00:00"))
                        added_count += 1
                
                if added_count > 0:
                    logger.info(f"➕ Добавлено {added_count} пользователей из таблицы 'tasks' (используется UTC)")
                logger.info(f"📊 Итого пользователей: {len(users)}")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось получить пользователей из таблицы 'tasks': {e}")
            
            return users
        except Exception as e:
            logger.error(f"❌ Ошибка при получении пользователей с часовым поясом: {e}", exc_info=True)
            return []
        finally:
            db.close()
            logger.debug("🔒 Соединение с базой данных закрыто")


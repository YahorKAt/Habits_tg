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
        db = SessionLocal()
        try:
            # Проверяем, существует ли таблица users
            try:
                db.execute(text("SELECT 1 FROM users LIMIT 1"))
            except Exception as e:
                logger.warning(f"⚠️ Table 'users' might not exist: {e}")
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


"""
Репозиторий для работы с пользователями
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from .. import models


class UserRepository:
    """Репозиторий для работы с пользователями"""
    
    @staticmethod
    def update_timezone(db: Session, user_id: int, timezone_offset: str) -> models.User:
        """Обновляет или создает запись о часовом поясе пользователя"""
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        if user:
            user.timezone_offset = timezone_offset
            user.updated_at = datetime.now(timezone.utc)
        else:
            user = models.User(user_id=user_id, timezone_offset=timezone_offset)
            db.add(user)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_timezone(db: Session, user_id: int) -> Optional[str]:
        """Получает часовой пояс пользователя"""
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        return user.timezone_offset if user else None
    
    @staticmethod
    def get_all_with_timezone(db: Session) -> List[models.User]:
        """Получает всех пользователей с сохраненным часовым поясом"""
        return db.query(models.User).filter(models.User.timezone_offset.isnot(None)).all()


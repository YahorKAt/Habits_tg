"""
Роутеры для работы со статистикой
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..dependencies import get_user_id
from ..repositories.stats_repository import StatsRepository
from .. import habits_stats

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats")
def stats(
    period: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Получает статистику по задачам"""
    logger.info(f"📊 Получен запрос на статистику за период '{period}' от пользователя {user_id}")
    if period not in {"day", "week", "month", "all"}:
        logger.warning(f"⚠️  Неверный период '{period}' от пользователя {user_id}")
        raise HTTPException(status_code=400, detail="Invalid period. Must be: day, week, month, or all")
    
    stats_data = StatsRepository.get_stats(db, user_id=user_id, period=period)
    logger.info(f"✅ Статистика за период '{period}' успешно возвращена для пользователя {user_id}")
    return stats_data


@router.get("/habits")
def habits_stats_endpoint(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Получает статистику по привычкам"""
    logger.info(f"📊 Получен запрос на статистику по привычкам от пользователя {user_id}")
    stats_data = habits_stats.get_habits_stats(db, user_id=user_id)
    logger.info(f"✅ Статистика по привычкам успешно возвращена для пользователя {user_id}")
    return stats_data


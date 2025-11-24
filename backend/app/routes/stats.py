"""
Роутеры для работы со статистикой
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_user_id
from ..repositories.stats_repository import StatsRepository
from .. import habits_stats

router = APIRouter()


@router.get("/stats")
def stats(
    period: str,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Получает статистику по задачам"""
    if period not in {"day", "week", "month", "all"}:
        raise HTTPException(status_code=400, detail="Invalid period. Must be: day, week, month, or all")
    
    return StatsRepository.get_stats(db, user_id=user_id, period=period)


@router.get("/habits")
def habits_stats_endpoint(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Получает статистику по привычкам"""
    return habits_stats.get_habits_stats(db, user_id=user_id)


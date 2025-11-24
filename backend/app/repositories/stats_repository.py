"""
Репозиторий для работы со статистикой
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Dict, Any

from .. import models
from ..repositories.user_repository import UserRepository


def parse_timezone_offset(offset_str: str) -> float:
    """Парсит строку часового пояса в число часов"""
    if not offset_str:
        return 0.0
    
    sign = 1 if offset_str[0] == '+' else -1
    hours = int(offset_str[1:3])
    minutes = int(offset_str[4:6]) if len(offset_str) > 4 else 0
    return sign * (hours + minutes / 60)


class StatsRepository:
    """Репозиторий для работы со статистикой"""
    
    @staticmethod
    def get_stats(db: Session, user_id: int, period: str) -> Dict[str, Any]:
        """
        Получает статистику по задачам для указанного периода.
        Учитывает только основные задачи, без подзадач.
        Оптимизировано для быстрой работы с большим количеством задач.
        Учитывает локальное время пользователя на основе его timezone.
        
        Периоды (по локальному времени пользователя):
        - "day" - сегодня
        - "week" - текущая неделя (с понедельника по локальному времени)
        - "month" - текущий месяц (с 1 числа по локальному времени)
        - "all" - все время
        """
        from datetime import datetime, timedelta, timezone
        from ..utils.date_utils import normalize_to_utc, normalize_date_to_utc_day
        
        # Получаем часовой пояс пользователя
        user_timezone_offset = UserRepository.get_timezone(db, user_id)
        
        # Используем timezone-aware datetime в UTC
        now_utc = datetime.now(timezone.utc)
        
        # Определяем границы периода в локальном времени пользователя, затем преобразуем в UTC
        user_tz = None
        now_user_tz = None
        period_start_utc = None
        period_end_utc = None
        
        if user_timezone_offset:
            try:
                offset_hours = parse_timezone_offset(user_timezone_offset)
                user_tz = timezone(timedelta(hours=offset_hours))
                now_user_tz = now_utc.astimezone(user_tz)
            except Exception:
                user_tz = None
        
        if user_tz and now_user_tz:
            # Определяем период в локальном времени пользователя
            if period == "day":
                day_start_user_local = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end_user_local = day_start_user_local + timedelta(days=1)
                period_start_utc = day_start_user_local.astimezone(timezone.utc)
                period_end_utc = day_end_user_local.astimezone(timezone.utc)
            elif period == "week":
                week_start_user_local = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now_user_tz.weekday())
                week_end_user_local = week_start_user_local + timedelta(days=7)
                period_start_utc = week_start_user_local.astimezone(timezone.utc)
                period_end_utc = week_end_user_local.astimezone(timezone.utc)
            elif period == "month":
                month_start_user_local = now_user_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if month_start_user_local.month == 12:
                    month_end_user_local = month_start_user_local.replace(year=month_start_user_local.year + 1, month=1)
                else:
                    month_end_user_local = month_start_user_local.replace(month=month_start_user_local.month + 1)
                period_start_utc = month_start_user_local.astimezone(timezone.utc)
                period_end_utc = month_end_user_local.astimezone(timezone.utc)
        else:
            # Если timezone не установлен, используем UTC
            today = normalize_date_to_utc_day(now_utc)
            if today is None:
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            if period == "day":
                period_start_utc = today
                period_end_utc = today + timedelta(days=1)
            elif period == "week":
                period_start_utc = today - timedelta(days=today.weekday())
                period_end_utc = period_start_utc + timedelta(days=7)
            elif period == "month":
                period_start_utc = today.replace(day=1)
                if period_start_utc.month == 12:
                    period_end_utc = period_start_utc.replace(year=period_start_utc.year + 1, month=1)
                else:
                    period_end_utc = period_start_utc.replace(month=period_start_utc.month + 1)
        
        # Базовые условия для запроса
        base_conditions = [models.Task.user_id == user_id]
        
        # Фильтруем задачи по периоду
        if period_start_utc is not None and period_end_utc is not None:
            base_conditions.append(models.Task.created_at >= period_start_utc)
            base_conditions.append(models.Task.created_at < period_end_utc)
        
        # Для периода "all" все выполненные задачи считаются выполненными
        if period == "all":
            all_conditions = [models.Task.user_id == user_id]
            completed = db.execute(
                select(func.count()).select_from(models.Task).where(
                    *all_conditions,
                    models.Task.completed == True,  # noqa: E712
                    models.Task.last_completed_date.isnot(None)
                )
            ).scalar() or 0
            in_progress = db.execute(
                select(func.count()).select_from(models.Task).where(
                    *all_conditions,
                    models.Task.completed == False  # noqa: E712
                )
            ).scalar() or 0
            upcoming = 0
        else:
            # Для других периодов нужно проверять дату выполнения
            tasks_query = select(
                models.Task.completed,
                models.Task.last_completed_date,
                models.Task.created_at
            ).where(*base_conditions)
            
            tasks = db.execute(tasks_query).all()
            
            completed = 0
            in_progress = 0
            upcoming = 0
            
            for task_row in tasks:
                task_completed, task_last_completed, task_created = task_row
                
                if task_completed and task_last_completed:
                    completed_date_utc = normalize_to_utc(task_last_completed)
                    
                    if completed_date_utc is None:
                        continue
                    
                    # Преобразуем дату выполнения в локальное время пользователя для сравнения
                    if user_tz:
                        completed_date_user_tz = completed_date_utc.astimezone(user_tz)
                        completed_date_user_local = completed_date_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
                    else:
                        completed_date_user_local = normalize_date_to_utc_day(completed_date_utc)
                    
                    # Проверяем, попадает ли дата выполнения в период
                    if period == "day":
                        if user_tz and now_user_tz:
                            day_start_user_local = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0)
                            if completed_date_user_local == day_start_user_local:
                                completed += 1
                            else:
                                in_progress += 1
                        else:
                            today_utc = normalize_date_to_utc_day(now_utc)
                            if completed_date_user_local == today_utc:
                                completed += 1
                            else:
                                in_progress += 1
                    elif period == "week":
                        if user_tz and now_user_tz:
                            week_start_user_local = now_user_tz.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now_user_tz.weekday())
                            completed_week_start_user_local = completed_date_user_tz.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=completed_date_user_tz.weekday())
                            if completed_week_start_user_local == week_start_user_local:
                                completed += 1
                            else:
                                in_progress += 1
                        else:
                            today_utc = normalize_date_to_utc_day(now_utc)
                            week_start_utc = today_utc - timedelta(days=today_utc.weekday())
                            completed_week_start_utc = completed_date_user_local - timedelta(days=completed_date_user_local.weekday())
                            if completed_week_start_utc == week_start_utc:
                                completed += 1
                            else:
                                in_progress += 1
                    elif period == "month":
                        if user_tz and now_user_tz:
                            month_start_user_local = now_user_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                            completed_month_start_user_local = completed_date_user_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                            if completed_month_start_user_local.date() == month_start_user_local.date():
                                completed += 1
                            else:
                                in_progress += 1
                        else:
                            today_utc = normalize_date_to_utc_day(now_utc)
                            month_start_utc = today_utc.replace(day=1)
                            completed_month_start_utc = completed_date_user_local.replace(day=1)
                            if completed_month_start_utc == month_start_utc:
                                completed += 1
                            else:
                                in_progress += 1
                else:
                    # Невыполненные задачи
                    task_created_utc = normalize_to_utc(task_created)
                    
                    if task_created_utc and period_start_utc and period_end_utc:
                        if period_start_utc <= task_created_utc < period_end_utc:
                            in_progress += 1
                        elif task_created_utc < period_start_utc:
                            upcoming += 1
        
        return {
            "period": period,
            "completed": completed,
            "in_progress": in_progress,
            "upcoming": upcoming,
            "total": completed + in_progress + upcoming,
        }


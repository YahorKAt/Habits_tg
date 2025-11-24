"""
Сервис для генерации задач по расписанию
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta, timezone
import logging

from .. import models
from ..repositories.task_repository import TaskRepository, SubtaskRepository
from ..repositories.user_repository import UserRepository
from ..utils.date_utils import normalize_to_utc, normalize_date_to_utc_day

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для генерации задач по расписанию"""
    
    @staticmethod
    def generate_daily_tasks(
        db: Session,
        target_date: Optional[datetime] = None,
        user_id: Optional[int] = None,
        is_user_timezone_start: bool = False
    ) -> int:
        """
        Генерирует задачи для нового дня.
        В 00:00 10 ноября создает задачи для 10 ноября на основе задач 9 ноября.
        
        Args:
            target_date: Дата, для которой нужно создать задачи (по умолчанию - сегодня)
            user_id: ID пользователя, для которого создавать задачи (если None - для всех пользователей)
            is_user_timezone_start: Если True, target_date уже представляет начало дня в часовом поясе пользователя (в UTC).
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc)
        
        # Нормализуем дату в UTC
        target_date = normalize_to_utc(target_date) or datetime.now(timezone.utc)
        
        # Если дата уже представляет начало дня в часовом поясе пользователя, используем как есть
        if is_user_timezone_start:
            prev_date = target_date - timedelta(days=1)
        else:
            target_date = normalize_date_to_utc_day(target_date) or target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_date = target_date - timedelta(days=1)
        
        # Создаем диапазоны для сравнения
        prev_date_start = prev_date
        prev_date_end = prev_date + timedelta(days=1)
        target_date_start = target_date
        target_date_end = target_date + timedelta(days=1)
        
        if user_id:
            logger.debug(f"Генерация задач для пользователя {user_id}, дата: {target_date.date()}")
        
        created_count = 0
        
        # Получаем список пользователей для обработки
        if user_id:
            all_user_ids = [user_id]
        else:
            all_user_ids = db.execute(
                select(models.Task.user_id).distinct()
            ).scalars().all()
        
        if not all_user_ids:
            logger.debug("Пользователи с задачами не найдены")
            return 0
        
        for user_id in all_user_ids:
            # Ищем все задачи предыдущего дня
            source_tasks = db.execute(
                select(models.Task)
                .where(
                    models.Task.user_id == user_id,
                    models.Task.frequency == 'daily',
                    models.Task.created_at >= prev_date_start,
                    models.Task.created_at < prev_date_end
                )
                .options(joinedload(models.Task.subtasks))
            ).unique().scalars().all()
            
            if len(source_tasks) == 0:
                logger.debug(f"Пользователь {user_id}: задачи не найдены за {prev_date.date()}")
                continue
            
            # Для каждой найденной задачи создаем новую задачу
            for source_task in source_tasks:
                # Проверяем, не истекла ли задача
                if source_task.end_date:
                    end_date = normalize_to_utc(source_task.end_date)
                    if end_date and target_date > end_date:
                        continue
                
                # Проверяем, была ли уже создана задача для этой даты
                existing_task = db.execute(
                    select(models.Task)
                    .where(
                        models.Task.user_id == user_id,
                        models.Task.frequency == 'daily',
                        models.Task.title == source_task.title,
                        models.Task.created_at >= target_date_start,
                        models.Task.created_at < target_date_end
                    )
                ).scalar_one_or_none()
                
                if existing_task:
                    continue
                
                # Определяем стрик на основе предыдущей задачи
                new_streak = 0
                if source_task.completed:
                    new_streak = source_task.streak + 1
                
                # Создаем новую независимую задачу
                new_task = models.Task(
                    user_id=user_id,
                    title=source_task.title,
                    description=source_task.description,
                    repeat_interval=source_task.repeat_interval,
                    next_due_date=None,
                    end_date=source_task.end_date,
                    category=source_task.category,
                    frequency=source_task.frequency,
                    completed=False,
                    streak=new_streak,
                    deleted=False
                )
                new_task.created_at = target_date
                db.add(new_task)
                db.flush()
                created_count += 1
                
                # Копируем подзадачи со статусом "не выполнено"
                for subtask in source_task.subtasks:
                    new_subtask = models.Subtask(
                        task_id=new_task.id,
                        title=subtask.title,
                        completed=False
                    )
                    new_subtask.created_at = target_date
                    db.add(new_subtask)
        
        if created_count > 0:
            db.commit()
            logger.debug(f"Создано {created_count} задач за {target_date.date()}")
        
        return created_count


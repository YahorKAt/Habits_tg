"""
Сервис для бизнес-логики работы с задачами
"""
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta

from .. import models
from ..repositories.task_repository import TaskRepository, SubtaskRepository
from ..utils.date_utils import (
    normalize_to_utc,
    get_today_utc,
    normalize_date_to_utc_day,
    is_past_date
)


class TaskService:
    """Сервис для работы с задачами"""
    
    @staticmethod
    def calculate_next_due_date(task: models.Task) -> Optional[datetime]:
        """
        Вычисляет следующую дату выполнения для повторяющейся задачи на основе frequency.
        Возвращает timezone-aware datetime в UTC.
        """
        if not task.frequency:
            return None
        
        base_date = task.last_completed_date or task.created_at
        if not base_date:
            return None
        
        base_date = normalize_to_utc(base_date)
        if base_date is None:
            return None
        
        if task.frequency == 'daily':
            return base_date + timedelta(days=task.repeat_interval)
        elif task.frequency == 'weekly':
            return base_date + timedelta(weeks=task.repeat_interval)
        elif task.frequency == 'monthly':
            return base_date + timedelta(days=30 * task.repeat_interval)
        
        return None
    
    @staticmethod
    def set_completed(
        db: Session,
        task_id: int,
        user_id: int,
        completed: bool,
        current_time: Optional[datetime] = None
    ) -> Optional[models.Task]:
        """Устанавливает статус выполнения задачи"""
        task = TaskRepository.get_by_id(db, task_id, user_id)
        if not task:
            return None
        
        # Используем утилиты для нормализации дат в UTC
        today = get_today_utc(current_time)
        yesterday = today - timedelta(days=1)
        
        # Нормализуем дату создания задачи в UTC для сравнения
        task_created_day = normalize_date_to_utc_day(task.created_at)
        
        # Сравниваем timezone-aware datetime
        if task_created_day is not None and yesterday is not None:
            if task_created_day < yesterday:
                raise ValueError("Cannot modify task status for past dates")
        
        # Нормализуем completion_date в UTC
        if current_time:
            completion_date = normalize_to_utc(current_time) or datetime.now(timezone.utc)
        else:
            completion_date = datetime.now(timezone.utc)
        
        if completed:
            next_due_date = None
            if task.frequency in ('daily', 'weekly', 'monthly'):
                next_due_date = TaskService.calculate_next_due_date(task)
            
            return TaskRepository.update_completion(
                db, task_id, user_id, completed,
                last_completed_date=completion_date,
                next_due_date=next_due_date
            )
        else:
            return TaskRepository.update_completion(
                db, task_id, user_id, completed,
                last_completed_date=None,
                next_due_date=None
            )
    
    @staticmethod
    def list_with_subtasks(
        db: Session,
        user_id: int,
        selected_date: Optional[datetime] = None,
        current_time: Optional[datetime] = None
    ) -> List[models.Task]:
        """
        Получает список задач с подзадачами для выбранной даты.
        Работает с реальными записями в БД (каждая дата имеет свою запись).
        """
        today = get_today_utc(current_time)
        
        if selected_date is None:
            selected_date = normalize_to_utc(current_time) or datetime.now(timezone.utc)
        
        # Нормализуем выбранную дату в UTC
        selected_day = normalize_date_to_utc_day(selected_date)
        
        # Создаем диапазон для выбранного дня в UTC
        if selected_day:
            selected_day_start = selected_day - timedelta(days=1)
            selected_day_end = selected_day + timedelta(days=2)
        else:
            selected_day_start = None
            selected_day_end = None
        
        # Определяем, является ли выбранная дата прошлой
        is_past = is_past_date(selected_day, today)
        
        # Получаем все задачи пользователя
        tasks = TaskRepository.get_all_by_user(db, user_id, with_subtasks=True)
        
        # Фильтруем задачи по выбранной дате
        filtered_tasks = []
        for task in tasks:
            task_created_day = normalize_date_to_utc_day(task.created_at)
            frequency = task.frequency
            
            should_show = False
            
            if frequency == 'daily':
                if task_created_day and selected_day_start and selected_day_end:
                    if selected_day_start <= task_created_day < selected_day_end:
                        should_show = True
            elif frequency == 'weekly':
                if task_created_day:
                    selected_week_start = selected_day - timedelta(days=selected_day.weekday())
                    task_week_start = task_created_day - timedelta(days=task_created_day.weekday())
                    if selected_week_start == task_week_start:
                        should_show = True
            elif frequency == 'monthly':
                if task_created_day:
                    selected_month_start = selected_day.replace(day=1)
                    task_month_start = task_created_day.replace(day=1)
                    if selected_month_start == task_month_start:
                        should_show = True
            
            if should_show:
                # Для прошлых дат: если задача не выполнена, все подзадачи тоже должны быть не выполнены
                if is_past and not task.completed:
                    for subtask in task.subtasks:
                        subtask.completed = False
                
                filtered_tasks.append(task)
        
        return filtered_tasks


class SubtaskService:
    """Сервис для работы с подзадачами"""
    
    @staticmethod
    def toggle_completion(
        db: Session,
        subtask_id: int,
        user_id: int
    ) -> Optional[models.Subtask]:
        """Переключает статус выполнения подзадачи"""
        subtask = SubtaskRepository.get_by_id(db, subtask_id)
        if not subtask:
            return None
        
        # Проверяем, что подзадача принадлежит задаче пользователя
        task = TaskRepository.get_by_id(db, subtask.task_id, user_id)
        if not task:
            return None
        
        new_completed_state = not subtask.completed
        return SubtaskRepository.update_completion(db, subtask_id, user_id, new_completed_state)


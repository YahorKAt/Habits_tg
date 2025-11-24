"""
Репозиторий для работы с задачами и подзадачами
"""
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime

from .. import models


class TaskRepository:
    """Репозиторий для работы с задачами"""
    
    @staticmethod
    def create(
        db: Session,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        repeat_interval: int = 1,
        next_due_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: str = 'personal',
        frequency: str = 'daily'
    ) -> models.Task:
        """Создает новую задачу"""
        # Преобразуем пустую строку в None для description
        if description is not None and description.strip() == '':
            description = None
        
        task = models.Task(
            user_id=user_id,
            title=title,
            description=description,
            repeat_interval=repeat_interval,
            next_due_date=next_due_date,
            end_date=end_date,
            category=category,
            frequency=frequency,
            streak=0  # Первая задача всегда со стриком 0
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def get_by_id(db: Session, task_id: int, user_id: int) -> Optional[models.Task]:
        """Получает задачу по ID"""
        return db.execute(
            select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user_id)
        ).scalar_one_or_none()
    
    @staticmethod
    def update(
        db: Session,
        task_id: int,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        repeat_interval: int = 1,
        next_due_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: str = 'personal',
        frequency: str = 'daily'
    ) -> Optional[models.Task]:
        """Обновляет задачу"""
        task = TaskRepository.get_by_id(db, task_id, user_id)
        if not task:
            return None
        
        task.title = title
        task.description = description
        task.repeat_interval = repeat_interval
        task.next_due_date = next_due_date
        task.end_date = end_date
        task.category = category
        task.frequency = frequency
        
        db.commit()
        db.refresh(task)
        return task
    
    @staticmethod
    def delete(db: Session, task_id: int, user_id: int) -> bool:
        """Удаляет задачу"""
        task = TaskRepository.get_by_id(db, task_id, user_id)
        if not task:
            return False
        
        db.delete(task)
        db.commit()
        return True
    
    @staticmethod
    def get_all_by_user(
        db: Session,
        user_id: int,
        with_subtasks: bool = True
    ) -> List[models.Task]:
        """Получает все задачи пользователя"""
        stmt = select(models.Task).where(models.Task.user_id == user_id)
        
        if with_subtasks:
            stmt = stmt.options(selectinload(models.Task.subtasks))
        
        stmt = stmt.order_by(models.Task.created_at.desc())
        return db.scalars(stmt).all()
    
    @staticmethod
    def get_by_date_range(
        db: Session,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[models.Task]:
        """Получает задачи в диапазоне дат"""
        stmt = select(models.Task).where(
            models.Task.user_id == user_id,
            models.Task.created_at >= start_date,
            models.Task.created_at < end_date
        ).options(selectinload(models.Task.subtasks))
        
        return db.scalars(stmt).all()
    
    @staticmethod
    def update_completion(
        db: Session,
        task_id: int,
        user_id: int,
        completed: bool,
        last_completed_date: Optional[datetime] = None,
        next_due_date: Optional[datetime] = None
    ) -> Optional[models.Task]:
        """Обновляет статус выполнения задачи"""
        task = TaskRepository.get_by_id(db, task_id, user_id)
        if not task:
            return None
        
        task.completed = completed
        if last_completed_date:
            task.last_completed_date = last_completed_date
        if next_due_date is not None:
            task.next_due_date = next_due_date
        
        db.commit()
        db.refresh(task)
        # Загружаем подзадачи
        _ = task.subtasks
        return task
    
    @staticmethod
    def update_streak(db: Session, task_id: int, streak: int) -> None:
        """Обновляет стрик задачи"""
        task = db.execute(
            select(models.Task).where(models.Task.id == task_id)
        ).scalar_one_or_none()
        
        if task:
            task.streak = streak
            db.commit()


class SubtaskRepository:
    """Репозиторий для работы с подзадачами"""
    
    @staticmethod
    def create(db: Session, task_id: int, user_id: int, title: str) -> Optional[models.Subtask]:
        """Создает подзадачу"""
        # Проверяем, что задача существует и принадлежит пользователю
        task = TaskRepository.get_by_id(db, task_id, user_id)
        if not task:
            return None
        
        subtask = models.Subtask(task_id=task_id, title=title)
        db.add(subtask)
        db.commit()
        db.refresh(subtask)
        return subtask
    
    @staticmethod
    def get_by_id(db: Session, subtask_id: int) -> Optional[models.Subtask]:
        """Получает подзадачу по ID"""
        return db.execute(
            select(models.Subtask).where(models.Subtask.id == subtask_id)
        ).scalar_one_or_none()
    
    @staticmethod
    def update(db: Session, subtask_id: int, user_id: int, title: str) -> Optional[models.Subtask]:
        """Обновляет подзадачу"""
        subtask = SubtaskRepository.get_by_id(db, subtask_id)
        if not subtask:
            return None
        
        # Проверяем, что подзадача принадлежит задаче пользователя
        task = TaskRepository.get_by_id(db, subtask.task_id, user_id)
        if not task:
            return None
        
        subtask.title = title
        db.commit()
        db.refresh(subtask)
        return subtask
    
    @staticmethod
    def delete(db: Session, subtask_id: int, user_id: int) -> bool:
        """Удаляет подзадачу"""
        subtask = SubtaskRepository.get_by_id(db, subtask_id)
        if not subtask:
            return False
        
        # Проверяем, что подзадача принадлежит задаче пользователя
        task = TaskRepository.get_by_id(db, subtask.task_id, user_id)
        if not task:
            return False
        
        db.delete(subtask)
        db.commit()
        return True
    
    @staticmethod
    def update_completion(
        db: Session,
        subtask_id: int,
        user_id: int,
        completed: bool
    ) -> Optional[models.Subtask]:
        """Обновляет статус выполнения подзадачи"""
        subtask = SubtaskRepository.get_by_id(db, subtask_id)
        if not subtask:
            return None
        
        # Проверяем, что подзадача принадлежит задаче пользователя
        task = TaskRepository.get_by_id(db, subtask.task_id, user_id)
        if not task:
            return None
        
        subtask.completed = completed
        db.commit()
        db.refresh(subtask)
        return subtask


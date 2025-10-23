from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from . import models
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


def create_task(db: Session, user_id: int, title: str, description=None, repeat_type=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> models.Task:
    task = models.Task(
        user_id=user_id, 
        title=title,
        description=description,
        repeat_type=repeat_type or models.RepeatType.NONE,
        repeat_interval=repeat_interval,
        next_due_date=next_due_date,
        end_date=end_date,
        category=category,
        frequency=frequency
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int, user_id: int) -> Optional[models.Task]:
    return db.execute(
        select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user_id)
    ).scalar_one_or_none()


def update_task(db: Session, task_id: int, user_id: int, title: str, description=None, repeat_type=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> Optional[models.Task]:
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return None
    
    task.title = title
    task.description = description
    task.repeat_type = repeat_type or models.RepeatType.NONE
    task.repeat_interval = repeat_interval
    task.next_due_date = next_due_date
    task.end_date = end_date
    task.category = category
    task.frequency = frequency
    
    db.commit()
    db.refresh(task)
    return task


def create_subtask(db: Session, task_id: int, title: str) -> models.Subtask:
    subtask = models.Subtask(task_id=task_id, title=title)
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask


def delete_subtask(db: Session, subtask_id: int, user_id: int) -> bool:
    subtask = db.execute(select(models.Subtask).where(models.Subtask.id == subtask_id)).scalar_one_or_none()
    if not subtask:
        return False
    # Ensure subtask belongs to user's task
    parent_task = get_task(db, task_id=subtask.task_id, user_id=user_id)
    if not parent_task:
        return False
    db.delete(subtask)
    db.commit()
    return True


def delete_task(db: Session, task_id: int, user_id: int) -> bool:
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True


def list_tasks_with_subtasks(db: Session, user_id: int):
    tasks = db.execute(select(models.Task).where(models.Task.user_id == user_id).order_by(models.Task.created_at.desc())).scalars().all()
    # Eagerly load subtasks
    for t in tasks:
        _ = t.subtasks  # access relationship
    return tasks


def set_task_completed(db: Session, task_id: int, user_id: int, completed: bool):
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return None
    
    if completed:
        task.last_completed_date = datetime.utcnow()
        # Если задача повторяющаяся, обновляем следующую дату выполнения
        if task.repeat_type != models.RepeatType.NONE:
            task.next_due_date = calculate_next_due_date(task)
    
    task.completed = completed
    db.commit()
    db.refresh(task)
    return task


def calculate_next_due_date(task: models.Task) -> Optional[datetime]:
    """Вычисляет следующую дату выполнения для повторяющейся задачи"""
    if task.repeat_type == models.RepeatType.NONE:
        return None
    
    base_date = task.last_completed_date or task.created_at
    if not base_date:
        return None
    
    if task.repeat_type == models.RepeatType.DAILY:
        return base_date + timedelta(days=task.repeat_interval)
    elif task.repeat_type == models.RepeatType.WEEKLY:
        return base_date + timedelta(weeks=task.repeat_interval)
    elif task.repeat_type == models.RepeatType.MONTHLY:
        # Простая логика для месяцев (30 дней)
        return base_date + timedelta(days=30 * task.repeat_interval)
    elif task.repeat_type == models.RepeatType.CUSTOM:
        # Для кастомного типа используем next_due_date если он задан
        return task.next_due_date
    
    return None


def set_subtask_completed(db: Session, subtask_id: int, user_id: int, completed: bool):
    subtask = db.execute(select(models.Subtask).where(models.Subtask.id == subtask_id)).scalar_one_or_none()
    if not subtask:
        return None
    # Ensure subtask belongs to user's task
    parent_task = get_task(db, task_id=subtask.task_id, user_id=user_id)
    if not parent_task:
        return None
    subtask.completed = completed
    db.commit()
    db.refresh(subtask)
    return subtask


def get_stats(db: Session, user_id: int, period: str):
    from datetime import datetime, timedelta

    since = None
    if period == "7":
        since = datetime.utcnow() - timedelta(days=7)
    elif period == "30":
        since = datetime.utcnow() - timedelta(days=30)

    task_query = select(func.count()).select_from(models.Task).where(
        models.Task.user_id == user_id, models.Task.completed == True  # noqa: E712
    )
    subtask_query = select(func.count()).select_from(models.Subtask).join(models.Task, models.Subtask.task_id == models.Task.id).where(
        models.Task.user_id == user_id, models.Subtask.completed == True  # noqa: E712
    )

    if since is not None:
        task_query = task_query.where(models.Task.created_at >= since)
        subtask_query = subtask_query.where(models.Subtask.created_at >= since)

    tasks_completed = db.execute(task_query).scalar() or 0
    subtasks_completed = db.execute(subtask_query).scalar() or 0

    return {
        "period": period,
        "tasks_completed": tasks_completed,
        "subtasks_completed": subtasks_completed,
        "total_completed": tasks_completed + subtasks_completed,
    }


def create_note(db: Session, user_id: int, content: str, date: str, mood: str = None):
    note = models.Note(
        user_id=user_id,
        content=content,
        date=date,
        mood=mood
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_notes_by_date(db: Session, user_id: int, date: str):
    return db.execute(
        select(models.Note)
        .where(models.Note.user_id == user_id, models.Note.date == date)
        .order_by(models.Note.created_at.desc())
    ).scalars().all()


def delete_note(db: Session, note_id: int, user_id: int) -> bool:
    note = db.execute(
        select(models.Note).where(models.Note.id == note_id, models.Note.user_id == user_id)
    ).scalar_one_or_none()
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True





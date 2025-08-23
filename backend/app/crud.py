from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select, func, update
from . import models
from typing import Optional, List, Dict, Any


def create_task(db: Session, user_id: int, title: str) -> models.Task:
    task = models.Task(user_id=user_id, title=title)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int, user_id: int) -> Optional[models.Task]:
    return db.execute(
        select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user_id)
    ).scalar_one_or_none()


def create_subtask(db: Session, task_id: int, title: str) -> models.Subtask:
    subtask = models.Subtask(task_id=task_id, title=title)
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask


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
    task.completed = completed
    db.commit()
    db.refresh(task)
    return task


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





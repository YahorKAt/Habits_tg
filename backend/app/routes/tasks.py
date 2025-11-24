"""
Роутеры для работы с задачами и подзадачами
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from ..database import get_db
from ..dependencies import get_user_id, get_client_time
from ..schemas import TaskCreate, SubtaskCreate, SubtaskUpdate
from ..repositories.task_repository import TaskRepository, SubtaskRepository
from ..services.task_service import TaskService, SubtaskService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/task")
def add_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Создает новую задачу"""
    try:
        task = TaskRepository.create(
            db,
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            repeat_interval=payload.repeat_interval,
            next_due_date=payload.next_due_date,
            end_date=payload.end_date,
            category=payload.category,
            frequency=payload.frequency
        )
        logger.debug(f"Создана задача: id={task.id}, title={payload.title[:30]}")
        return task
    except Exception as e:
        logger.error(f"Ошибка создания задачи: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.put("/task/{task_id}")
def update_task(
    task_id: int,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    client_time: datetime = Depends(get_client_time)
):
    """Обновляет задачу"""
    try:
        task = TaskRepository.update(
            db,
            task_id=task_id,
            user_id=user_id,
            title=payload.title,
            description=payload.description,
            repeat_interval=payload.repeat_interval,
            next_due_date=payload.next_due_date,
            end_date=payload.end_date,
            category=payload.category,
            frequency=payload.frequency
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/task/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    client_time: datetime = Depends(get_client_time)
):
    """Удаляет задачу"""
    try:
        deleted = TaskRepository.delete(db, task_id=task_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks")
def list_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    date: str = None,
    client_time: datetime = Depends(get_client_time),
):
    """Получает список задач с подзадачами"""
    try:
        selected_date = None
        if date:
            try:
                from datetime import datetime, timezone, timedelta
                local_date = datetime.strptime(date, "%Y-%m-%d")
                selected_date = local_date.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        
        return TaskService.list_with_subtasks(db, user_id=user_id, selected_date=selected_date, current_time=client_time)
    except Exception as e:
        logger.error(f"Ошибка получения списка задач: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@router.post("/task/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Переключает статус выполнения задачи"""
    try:
        task = TaskRepository.get_by_id(db, task_id=task_id, user_id=user_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        new_completed_state = not task.completed
        task = TaskService.set_completed(db, task_id=task_id, user_id=user_id, completed=new_completed_state)
        return task
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/generate-today")
def generate_today_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Ручной запуск генерации задач для сегодняшнего дня"""
    try:
        from datetime import datetime
        from ..services.scheduler_service import SchedulerService
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = SchedulerService.generate_daily_tasks(db, today)
        logger.info(f"Ручная генерация: создано {count} задач за {today.date()}")
        return {
            "ok": True,
            "date": today.isoformat(),
            "tasks_created": count,
            "message": f"Created {count} tasks for {today.date()}"
        }
    except Exception as e:
        logger.error(f"Ошибка ручной генерации задач: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate tasks: {str(e)}")


@router.post("/subtask")
def add_subtask(
    payload: SubtaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Создает новую подзадачу"""
    task = TaskRepository.get_by_id(db, task_id=payload.task_id, user_id=user_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    subtask = SubtaskRepository.create(db, task_id=payload.task_id, user_id=user_id, title=payload.title)
    return subtask


@router.put("/subtask/{subtask_id}")
def update_subtask(
    subtask_id: int,
    payload: SubtaskUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Обновляет подзадачу"""
    subtask = SubtaskRepository.update(db, subtask_id=subtask_id, user_id=user_id, title=payload.title)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask


@router.delete("/subtask/{subtask_id}")
def delete_subtask(
    subtask_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Удаляет подзадачу"""
    deleted = SubtaskRepository.delete(db, subtask_id=subtask_id, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return {"ok": True}


@router.post("/subtask/{subtask_id}/complete")
def complete_subtask(
    subtask_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Переключает статус выполнения подзадачи"""
    subtask = SubtaskService.toggle_completion(db, subtask_id=subtask_id, user_id=user_id)
    if not subtask:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return subtask


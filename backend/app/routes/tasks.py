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
    logger.info(f"📝 Получен запрос на создание задачи от пользователя {user_id}")
    logger.debug(f"   Данные задачи: title='{payload.title[:50]}', category={payload.category}, frequency={payload.frequency}")
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
        logger.info(f"✅ Задача успешно создана: id={task.id}, title='{payload.title[:50]}' для пользователя {user_id}")
        return task
    except Exception as e:
        logger.error(f"❌ Ошибка создания задачи для пользователя {user_id}: {e}", exc_info=True)
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
    logger.info(f"✏️  Получен запрос на обновление задачи {task_id} от пользователя {user_id}")
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
            logger.warning(f"⚠️  Задача {task_id} не найдена для пользователя {user_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info(f"✅ Задача {task_id} успешно обновлена для пользователя {user_id}")
        return task
    except ValueError as e:
        logger.error(f"❌ Ошибка валидации при обновлении задачи {task_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/task/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    client_time: datetime = Depends(get_client_time)
):
    """Удаляет задачу"""
    logger.info(f"🗑️  Получен запрос на удаление задачи {task_id} от пользователя {user_id}")
    try:
        deleted = TaskRepository.delete(db, task_id=task_id, user_id=user_id)
        if not deleted:
            logger.warning(f"⚠️  Задача {task_id} не найдена для удаления пользователем {user_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info(f"✅ Задача {task_id} успешно удалена пользователем {user_id}")
        return {"ok": True}
    except ValueError as e:
        logger.error(f"❌ Ошибка валидации при удалении задачи {task_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks")
def list_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id),
    date: str = None,
    client_time: datetime = Depends(get_client_time),
):
    """Получает список задач с подзадачами"""
    logger.info(f"📋 Получен запрос на список задач от пользователя {user_id}" + (f" для даты {date}" if date else ""))
    try:
        selected_date = None
        if date:
            try:
                from datetime import datetime, timezone, timedelta
                local_date = datetime.strptime(date, "%Y-%m-%d")
                selected_date = local_date.replace(tzinfo=timezone.utc)
                logger.debug(f"   Выбранная дата: {date}")
            except ValueError:
                logger.warning(f"⚠️  Неверный формат даты: {date}")
                pass
        
        tasks = TaskService.list_with_subtasks(db, user_id=user_id, selected_date=selected_date, current_time=client_time)
        logger.info(f"✅ Возвращено {len(tasks)} задач для пользователя {user_id}")
        return tasks
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка задач для пользователя {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@router.post("/task/{task_id}/complete")
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Переключает статус выполнения задачи"""
    logger.info(f"✅ Получен запрос на переключение статуса задачи {task_id} от пользователя {user_id}")
    try:
        task = TaskRepository.get_by_id(db, task_id=task_id, user_id=user_id)
        if not task:
            logger.warning(f"⚠️  Задача {task_id} не найдена для пользователя {user_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        
        new_completed_state = not task.completed
        logger.debug(f"   Текущий статус: {task.completed}, новый статус: {new_completed_state}")
        task = TaskService.set_completed(db, task_id=task_id, user_id=user_id, completed=new_completed_state)
        logger.info(f"✅ Статус задачи {task_id} изменен на {'выполнено' if new_completed_state else 'не выполнено'} для пользователя {user_id}")
        return task
    except ValueError as e:
        logger.error(f"❌ Ошибка валидации при переключении статуса задачи {task_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tasks/generate-today")
def generate_today_tasks(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Ручной запуск генерации задач для сегодняшнего дня"""
    logger.info(f"🔄 Получен запрос на ручную генерацию задач для пользователя {user_id}")
    try:
        from datetime import datetime
        from ..services.scheduler_service import SchedulerService
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        logger.debug(f"   Генерация задач для даты: {today.date()}")
        count = SchedulerService.generate_daily_tasks(db, today, user_id=user_id)
        logger.info(f"✅ Ручная генерация завершена: создано {count} задач для пользователя {user_id} за {today.date()}")
        return {
            "ok": True,
            "date": today.isoformat(),
            "tasks_created": count,
            "message": f"Created {count} tasks for {today.date()}"
        }
    except Exception as e:
        logger.error(f"❌ Ошибка ручной генерации задач для пользователя {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate tasks: {str(e)}")


@router.post("/subtask")
def add_subtask(
    payload: SubtaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Создает новую подзадачу"""
    logger.info(f"📝 Получен запрос на создание подзадачи для задачи {payload.task_id} от пользователя {user_id}")
    task = TaskRepository.get_by_id(db, task_id=payload.task_id, user_id=user_id)
    if not task:
        logger.warning(f"⚠️  Задача {payload.task_id} не найдена для создания подзадачи пользователем {user_id}")
        raise HTTPException(status_code=404, detail="Task not found")
    
    subtask = SubtaskRepository.create(db, task_id=payload.task_id, user_id=user_id, title=payload.title)
    logger.info(f"✅ Подзадача {subtask.id} успешно создана для задачи {payload.task_id} пользователем {user_id}")
    return subtask


@router.put("/subtask/{subtask_id}")
def update_subtask(
    subtask_id: int,
    payload: SubtaskUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Обновляет подзадачу"""
    logger.info(f"✏️  Получен запрос на обновление подзадачи {subtask_id} от пользователя {user_id}")
    subtask = SubtaskRepository.update(db, subtask_id=subtask_id, user_id=user_id, title=payload.title)
    if not subtask:
        logger.warning(f"⚠️  Подзадача {subtask_id} не найдена для обновления пользователем {user_id}")
        raise HTTPException(status_code=404, detail="Subtask not found")
    logger.info(f"✅ Подзадача {subtask_id} успешно обновлена пользователем {user_id}")
    return subtask


@router.delete("/subtask/{subtask_id}")
def delete_subtask(
    subtask_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Удаляет подзадачу"""
    logger.info(f"🗑️  Получен запрос на удаление подзадачи {subtask_id} от пользователя {user_id}")
    deleted = SubtaskRepository.delete(db, subtask_id=subtask_id, user_id=user_id)
    if not deleted:
        logger.warning(f"⚠️  Подзадача {subtask_id} не найдена для удаления пользователем {user_id}")
        raise HTTPException(status_code=404, detail="Subtask not found")
    logger.info(f"✅ Подзадача {subtask_id} успешно удалена пользователем {user_id}")
    return {"ok": True}


@router.post("/subtask/{subtask_id}/complete")
def complete_subtask(
    subtask_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_user_id)
):
    """Переключает статус выполнения подзадачи"""
    logger.info(f"✅ Получен запрос на переключение статуса подзадачи {subtask_id} от пользователя {user_id}")
    subtask = SubtaskService.toggle_completion(db, subtask_id=subtask_id, user_id=user_id)
    if not subtask:
        logger.warning(f"⚠️  Подзадача {subtask_id} не найдена для переключения статуса пользователем {user_id}")
        raise HTTPException(status_code=404, detail="Subtask not found")
    logger.info(f"✅ Статус подзадачи {subtask_id} изменен на {'выполнено' if subtask.completed else 'не выполнено'} для пользователя {user_id}")
    return subtask


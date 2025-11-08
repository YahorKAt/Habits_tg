from __future__ import annotations

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, update
from . import models
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger(__name__)


def create_task(db: Session, user_id: int, title: str, description=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> models.Task:
    # Преобразуем пустую строку в None для description
    if description is not None and description.strip() == '':
        description = None
    
    # Создаем оригинальную задачу (parent_task_id = None)
    # Оригинальная задача уже является задачей для дня создания (created_at = сегодня)
    # Для будущих дней будут создаваться дочерние задачи через generate_daily_tasks()
    task = models.Task(
        user_id=user_id, 
        title=title,
        description=description,
        repeat_interval=repeat_interval,
        next_due_date=next_due_date,
        end_date=end_date,
        category=category,
        frequency=frequency,
        parent_task_id=None  # Оригинальная задача не имеет родителя
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    return task


def get_task(db: Session, task_id: int, user_id: int) -> Optional[models.Task]:
    return db.execute(
        select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user_id)
    ).scalar_one_or_none()


def update_task(db: Session, task_id: int, user_id: int, title: str, description=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> Optional[models.Task]:
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return None
    
    # Проверяем, не является ли дата создания задачи будущей датой
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
    if task_created_day and task_created_day.tzinfo is None:
        task_created_day = task_created_day.replace(tzinfo=timezone.utc)
    
    if task_created_day and task_created_day > today:
        # Нельзя редактировать задачи для будущих дат
        raise ValueError("Cannot edit tasks for future dates")
    
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
    """
    Мягкое удаление задачи - помечает как удаленную, но не удаляет из БД.
    Удаленная задача остается в архиве и показывается только для прошлых дат.
    """
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return False
    
    # Проверяем, не является ли дата создания задачи будущей датой
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
    if task_created_day and task_created_day.tzinfo is None:
        task_created_day = task_created_day.replace(tzinfo=timezone.utc)
    
    if task_created_day and task_created_day > today:
        # Нельзя удалять задачи для будущих дат
        raise ValueError("Cannot delete tasks for future dates")
    
    task.deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def list_tasks_with_subtasks(db: Session, user_id: int, selected_date: datetime = None):
    """
    Получает список задач с подзадачами для выбранной даты.
    Работает с реальными записями в БД (каждая дата имеет свою запись).
    
    Args:
        selected_date: Дата для фильтрации задач (если None - используется текущая дата)
    """
    now = datetime.now(timezone.utc)
    if selected_date is None:
        selected_date = now
    
    # Подготавливаем нормализованные даты один раз (timezone-aware)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    selected_day = selected_date.replace(hour=0, minute=0, second=0, microsecond=0) if selected_date.tzinfo else selected_date.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)
    
    # Убеждаемся, что все даты timezone-aware
    if selected_day.tzinfo is None:
        selected_day = selected_day.replace(tzinfo=timezone.utc)
    if today.tzinfo is None:
        today = today.replace(tzinfo=timezone.utc)
    
    # Для будущих дат или сегодня - генерируем задачи если их еще нет
    if selected_day >= today:
        generate_daily_tasks(db, selected_day)
    
    # Получаем задачи для выбранной даты
    # Фильтруем по created_at = selected_day (для ежедневных задач)
    # Или по неделе/месяцу для еженедельных/месячных задач
    is_past_date = selected_day < today
    stmt = select(models.Task).where(models.Task.user_id == user_id)
    
    # Если выбран прошлый день - показываем все задачи (включая удаленные)
    # Если выбран сегодня или будущее - показываем только не удаленные
    if not is_past_date:
        stmt = stmt.where(models.Task.deleted == False)
    
    stmt = stmt.options(joinedload(models.Task.subtasks)).order_by(models.Task.created_at.desc())
    result = db.execute(stmt)
    tasks = result.unique().scalars().all()
    
    # Фильтруем задачи по выбранной дате
    filtered_tasks = []
    for task in tasks:
        task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
        # Убеждаемся, что task_created_day timezone-aware для сравнения
        if task_created_day and task_created_day.tzinfo is None:
            task_created_day = task_created_day.replace(tzinfo=timezone.utc)
        
        # Удаленные задачи показываем только для прошлых дат
        if task.deleted:
            if not is_past_date:
                continue
        
        frequency = task.frequency
        
        # Фильтруем задачи по дате создания
        should_show = False
        
        # Проверяем, является ли это оригинальной задачей (parent_task_id = NULL)
        is_original_task = task.parent_task_id is None
        
        if frequency == 'daily':
            # Ежедневные задачи
            if task_created_day and task_created_day == selected_day:
                # Показываем оригинальную задачу для дня её создания
                # Или дочернюю задачу для соответствующего дня
                should_show = True
        
        elif frequency == 'weekly':
            # Еженедельные задачи - показываем задачи, созданные в выбранную неделю
            if task_created_day:
                selected_week_start = selected_day - timedelta(days=selected_day.weekday())
                task_week_start = task_created_day - timedelta(days=task_created_day.weekday())
                if selected_week_start == task_week_start:
                    # Показываем оригинальную задачу для недели её создания
                    # Или дочернюю задачу для соответствующей недели
                    should_show = True
        
        elif frequency == 'monthly':
            # Месячные задачи - показываем задачи, созданные в выбранный месяц
            if task_created_day:
                selected_month_start = selected_day.replace(day=1)
                task_month_start = task_created_day.replace(day=1)
                if selected_month_start == task_month_start:
                    # Показываем оригинальную задачу для месяца её создания
                    # Или дочернюю задачу для соответствующего месяца
                    should_show = True
        
        if should_show:
            # Статус выполнения уже установлен в поле completed при создании задачи
            # Для прошлых дат: если задача не выполнена, все подзадачи тоже должны быть не выполнены
            if is_past_date and not task.completed:
                for subtask in task.subtasks:
                    subtask.completed = False
            
            filtered_tasks.append(task)
    
    return filtered_tasks


def set_task_completed(db: Session, task_id: int, user_id: int, completed: bool):
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return None
    
    # Проверяем, не является ли дата создания задачи будущей датой
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
    if task_created_day and task_created_day.tzinfo is None:
        task_created_day = task_created_day.replace(tzinfo=timezone.utc)
    
    if task_created_day and task_created_day > today:
        # Нельзя изменять статус задач для будущих дат
        raise ValueError("Cannot modify task status for future dates")
    
    completion_date = datetime.now(timezone.utc)
    
    if completed:
        task.last_completed_date = completion_date
        # Вычисляем новый стрик
        task.streak = calculate_streak_on_complete(task, completion_date)
        # Если задача повторяющаяся (на основе frequency), обновляем следующую дату выполнения
        if task.frequency in ('daily', 'weekly', 'monthly'):
            task.next_due_date = calculate_next_due_date(task)
    else:
        # При отмене выполнения сбрасываем дату, стрик и следующую дату выполнения
        task.last_completed_date = None
        task.streak = 0
        task.next_due_date = None
    
    task.completed = completed
    db.commit()
    db.refresh(task)
    # Явно загружаем подзадачи, чтобы они были включены в ответ
    _ = task.subtasks  # access relationship to load subtasks
    return task


def calculate_next_due_date(task: models.Task) -> Optional[datetime]:
    """Вычисляет следующую дату выполнения для повторяющейся задачи на основе frequency"""
    if not task.frequency:
        return None
    
    base_date = task.last_completed_date or task.created_at
    if not base_date:
        return None
    
    if task.frequency == 'daily':
        return base_date + timedelta(days=task.repeat_interval)
    elif task.frequency == 'weekly':
        return base_date + timedelta(weeks=task.repeat_interval)
    elif task.frequency == 'monthly':
        # Простая логика для месяцев (30 дней)
        return base_date + timedelta(days=30 * task.repeat_interval)
    
    return None


def calculate_streak_on_complete(task: models.Task, completion_date: datetime = None) -> int:
    """
    Вычисляет новый стрик при выполнении задачи.
    Если задача была выполнена в предыдущем периоде - стрик продолжается, иначе сбрасывается или начинается с 1.
    """
    if completion_date is None:
        completion_date = datetime.now(timezone.utc)
    
    # Приводим к UTC
    if completion_date.tzinfo is None:
        completion_date = completion_date.replace(tzinfo=timezone.utc)
    
    frequency = task.frequency
    
    # Используем старый last_completed_date для проверки непрерывности
    # (до того как мы обновим его в set_task_completed)
    old_last_completed = task.last_completed_date
    
    # Если это первое выполнение - стрик = 1
    if not old_last_completed:
        return 1
    
    last_completed = old_last_completed
    if last_completed.tzinfo is None:
        last_completed = last_completed.replace(tzinfo=timezone.utc)
    
    # Для daily - проверяем последовательность дней
    if frequency == 'daily':
        last_day = last_completed.replace(hour=0, minute=0, second=0, microsecond=0)
        completion_day = completion_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Если выполнение в тот же день - не меняем стрик
        if last_day == completion_day:
            return task.streak
        
        # Если выполнение было вчера - стрик продолжается
        yesterday = completion_day - timedelta(days=1)
        if last_day == yesterday:
            return task.streak + 1
        
        # Если пропущен день или больше - сбрасываем
        return 1
    
    # Для weekly - проверяем последовательность недель
    elif frequency == 'weekly':
        last_week_start = last_completed - timedelta(days=last_completed.weekday())
        last_week_start = last_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        completion_week_start = completion_date - timedelta(days=completion_date.weekday())
        completion_week_start = completion_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Если выполнение в ту же неделю - не меняем стрик
        if last_week_start == completion_week_start:
            return task.streak
        
        # Если выполнение было на прошлой неделе - стрик продолжается
        last_week = completion_week_start - timedelta(weeks=1)
        if last_week_start == last_week:
            return task.streak + 1
        
        # Если пропущена неделя или больше - сбрасываем
        return 1
    
    # Для monthly - проверяем последовательность месяцев
    elif frequency == 'monthly':
        last_month_start = last_completed.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        completion_month_start = completion_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Если выполнение в тот же месяц - не меняем стрик
        if last_month_start == completion_month_start:
            return task.streak
        
        # Если выполнение было в прошлом месяце - стрик продолжается
        last_month = completion_month_start - relativedelta(months=1)
        if last_month_start == last_month:
            return task.streak + 1
        
        # Если пропущен месяц или больше - сбрасываем
        return 1
    
    return 0


def reset_streak_if_missed(task: models.Task, now: datetime = None) -> int:
    """
    Проверяет и сбрасывает стрик если был пропущен период.
    Вызывается для обновления стрика при проверке задач.
    """
    if not task.last_completed_date:
        return 0
    
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Приводим к UTC (timezone-aware)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if task.last_completed_date:
        if task.last_completed_date.tzinfo is None:
            last_completed = task.last_completed_date.replace(tzinfo=timezone.utc)
        else:
            last_completed = task.last_completed_date
    else:
        return 0
    
    frequency = task.frequency
    
    # Для daily - проверяем пропуск дня
    if frequency == 'daily':
        last_day = last_completed.replace(hour=0, minute=0, second=0, microsecond=0)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Если последнее выполнение было больше чем вчера - сбрасываем стрик
        days_diff = (today - last_day).days
        if days_diff > 1:
            return 0  # Сброс стрика
        
        return task.streak
    
    # Для weekly - проверяем пропуск недели
    elif frequency == 'weekly':
        last_week_start = last_completed - timedelta(days=last_completed.weekday())
        last_week_start = last_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        current_week_start = now - timedelta(days=now.weekday())
        current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Если последнее выполнение было больше чем неделю назад - сбрасываем стрик
        weeks_diff = (current_week_start - last_week_start).days // 7
        if weeks_diff > 1:
            return 0  # Сброс стрика
        
        return task.streak
    
    # Для monthly - проверяем пропуск месяца
    elif frequency == 'monthly':
        last_month_start = last_completed.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Если последнее выполнение было больше чем месяц назад - сбрасываем стрик
        months_diff = (current_month_start.year - last_month_start.year) * 12 + (current_month_start.month - last_month_start.month)
        if months_diff > 1:
            return 0  # Сброс стрика
        
        return task.streak
    
    return task.streak


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


def update_subtask(db: Session, subtask_id: int, user_id: int, title: str):
    subtask = db.execute(select(models.Subtask).where(models.Subtask.id == subtask_id)).scalar_one_or_none()
    if not subtask:
        return None
    # Ensure subtask belongs to user's task
    parent_task = get_task(db, task_id=subtask.task_id, user_id=user_id)
    if not parent_task:
        return None
    subtask.title = title
    db.commit()
    db.refresh(subtask)
    return subtask


def get_stats(db: Session, user_id: int, period: str):
    """
    Получает статистику по задачам для указанного периода.
    Учитывает только основные задачи, без подзадач.
    Оптимизировано для быстрой работы с большим количеством задач.
    
    Периоды:
    - "day" - сегодня
    - "week" - текущая неделя
    - "month" - текущий месяц
    - "all" - все время
    """
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Определяем период фильтрации
    since = None
    if period == "day":
        since = today
    elif period == "week":
        # Начало текущей недели (понедельник)
        since = today - timedelta(days=today.weekday())
    elif period == "month":
        # Начало текущего месяца
        since = today.replace(day=1)
    # elif period == "all": since остается None
    
    # Базовые условия для запроса
    base_conditions = [
        models.Task.user_id == user_id,
        models.Task.deleted == False
    ]
    
    if since is not None:
        base_conditions.append(models.Task.created_at >= since)
    
    # Подсчитываем выполненные задачи (используя COUNT вместо загрузки всех задач)
    completed_query = select(func.count()).select_from(models.Task).where(
        *base_conditions,
        models.Task.completed == True,  # noqa: E712
        models.Task.last_completed_date.isnot(None)
    )
    
    # Для периода "all" все выполненные задачи считаются выполненными
    if period == "all":
        completed = db.execute(completed_query).scalar() or 0
        in_progress_query = select(func.count()).select_from(models.Task).where(
            *base_conditions,
            models.Task.completed == False  # noqa: E712
        )
        in_progress = db.execute(in_progress_query).scalar() or 0
        upcoming = 0
    else:
        # Для других периодов нужно проверять дату выполнения
        # Получаем только необходимые поля для фильтрации
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
                completed_date = task_last_completed.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Для периода "day" проверяем, что задача выполнена сегодня
                if period == "day":
                    if completed_date == today:
                        completed += 1
                    else:
                        in_progress += 1
                # Для периода "week" проверяем, что задача выполнена на этой неделе
                elif period == "week":
                    week_start = today - timedelta(days=today.weekday())
                    completed_week_start = completed_date - timedelta(days=completed_date.weekday())
                    if completed_week_start == week_start:
                        completed += 1
                    else:
                        in_progress += 1
                # Для периода "month" проверяем, что задача выполнена в этом месяце
                elif period == "month":
                    month_start = today.replace(day=1)
                    completed_month_start = completed_date.replace(day=1)
                    if completed_month_start == month_start:
                        completed += 1
                    else:
                        in_progress += 1
            # Невыполненные задачи
            else:
                task_created_day = task_created.replace(hour=0, minute=0, second=0, microsecond=0) if task_created else None
                
                if task_created_day and since and task_created_day >= since:
                    # Задача создана в этом периоде и не выполнена - в процессе
                    in_progress += 1
                elif task_created_day and since and task_created_day < since:
                    # Задача создана до периода и не выполнена - предстоящая
                    upcoming += 1
    
    return {
        "period": period,
        "completed": completed,
        "in_progress": in_progress,
        "upcoming": upcoming,
        "total": completed + in_progress + upcoming,
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


def generate_daily_tasks(db: Session, target_date: datetime = None):
    """
    Генерирует задачи для нового дня/недели/месяца.
    Вызывается автоматически при наступлении 00:00.
    
    Args:
        target_date: Дата, для которой нужно создать задачи (по умолчанию - сегодня)
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc)
    
    target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    target_week_start = target_date - timedelta(days=target_date.weekday())
    target_month_start = target_date.replace(day=1)
    
    # Получаем все оригинальные задачи (без parent_task_id) для всех пользователей
    original_tasks = db.execute(
        select(models.Task)
        .where(
            models.Task.parent_task_id == None,
            models.Task.deleted == False
        )
    ).scalars().all()
    
    created_count = 0
    
    for original_task in original_tasks:
        # Проверяем, не истекла ли задача
        if original_task.end_date and target_date > original_task.end_date.replace(tzinfo=timezone.utc):
            continue
        
        # Проверяем, была ли уже создана задача для этой даты/недели/месяца
        existing_task = None
        if original_task.frequency == 'daily':
            # Для ежедневных задач проверяем по конкретной дате
            existing_task = db.execute(
                select(models.Task)
                .where(
                    models.Task.parent_task_id == original_task.id,
                    models.Task.user_id == original_task.user_id,
                    func.date(models.Task.created_at) == func.date(target_date)
                )
            ).scalar_one_or_none()
        elif original_task.frequency == 'weekly':
            # Для еженедельных задач проверяем по неделе
            existing_task = db.execute(
                select(models.Task)
                .where(
                    models.Task.parent_task_id == original_task.id,
                    models.Task.user_id == original_task.user_id,
                    func.date(models.Task.created_at) >= func.date(target_week_start),
                    func.date(models.Task.created_at) < func.date(target_week_start + timedelta(days=7))
                )
            ).scalar_one_or_none()
        elif original_task.frequency == 'monthly':
            # Для месячных задач проверяем по месяцу
            next_month_start = (target_month_start + relativedelta(months=1)).replace(day=1)
            existing_task = db.execute(
                select(models.Task)
                .where(
                    models.Task.parent_task_id == original_task.id,
                    models.Task.user_id == original_task.user_id,
                    func.date(models.Task.created_at) >= func.date(target_month_start),
                    func.date(models.Task.created_at) < func.date(next_month_start)
                )
            ).scalar_one_or_none()
        
        if existing_task:
            continue  # Задача уже создана для этого периода
        
        # Определяем, нужно ли создавать задачу для этой даты
        should_create = False
        
        if original_task.frequency == 'daily':
            # Ежедневные задачи - создаем для каждого дня ПОСЛЕ created_at (не в тот же день)
            task_created_day = original_task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if original_task.created_at else None
            if task_created_day and target_date > task_created_day:  # Строго больше, не равно
                # Проверяем, не была ли задача удалена до этой даты
                if original_task.deleted_at:
                    deleted_day = original_task.deleted_at.replace(hour=0, minute=0, second=0, microsecond=0)
                    if target_date >= deleted_day:
                        continue  # Не создаем задачи после удаления
                should_create = True
        
        elif original_task.frequency == 'weekly':
            # Еженедельные задачи - создаем в начале каждой недели ПОСЛЕ недели создания
            task_created_day = original_task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if original_task.created_at else None
            if task_created_day:
                task_week_start = task_created_day - timedelta(days=task_created_day.weekday())
                # Создаем только если это не та же неделя, что и создание, и это понедельник
                if target_week_start > task_week_start and target_date.weekday() == 0:  # Строго больше
                    should_create = True
        
        elif original_task.frequency == 'monthly':
            # Месячные задачи - создаем в начале каждого месяца ПОСЛЕ месяца создания
            task_created_day = original_task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if original_task.created_at else None
            if task_created_day:
                task_month_start = task_created_day.replace(day=1)
                # Создаем только если это не тот же месяц, что и создание, и это 1-го числа
                if target_month_start > task_month_start and target_date.day == 1:  # Строго больше
                    should_create = True
        
        if should_create:
            # Создаем новую задачу для этой даты
            new_task = models.Task(
                user_id=original_task.user_id,
                title=original_task.title,
                description=original_task.description,
                repeat_interval=original_task.repeat_interval,
                next_due_date=None,
                end_date=original_task.end_date,
                category=original_task.category,
                frequency=original_task.frequency,
                parent_task_id=original_task.id,
                completed=False,
                streak=0,
                deleted=False
            )
            # Устанавливаем created_at в target_date
            new_task.created_at = target_date
            db.add(new_task)
            created_count += 1
            
            # Копируем подзадачи из оригинальной задачи
            for subtask in original_task.subtasks:
                new_subtask = models.Subtask(
                    task_id=new_task.id,
                    title=subtask.title,
                    completed=False
                )
                new_subtask.created_at = target_date
                db.add(new_subtask)
    
    if created_count > 0:
        db.commit()
        logger.info(f"✅ Created {created_count} tasks for {target_date.date()}")
    
    return created_count





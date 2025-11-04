from __future__ import annotations

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, update
from . import models
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


def create_task(db: Session, user_id: int, title: str, description=None, repeat_type=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> models.Task:
    # Преобразуем пустую строку в None для description
    if description is not None and description.strip() == '':
        description = None
    
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
    """
    Мягкое удаление задачи - помечает как удаленную, но не удаляет из БД.
    Удаленная задача остается в архиве и показывается только для прошлых дат.
    """
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return False
    task.deleted = True
    task.deleted_at = datetime.utcnow()
    db.commit()
    return True


def list_tasks_with_subtasks(db: Session, user_id: int, selected_date: datetime = None):
    """
    Получает список задач с подзадачами и автоматически обновляет их состояние.
    Оптимизировано для быстрой загрузки.
    
    Args:
        selected_date: Дата для фильтрации задач (если None - используется текущая дата)
    """
    now = datetime.utcnow()
    if selected_date is None:
        selected_date = now
    
    # Подготавливаем нормализованные даты один раз
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    selected_day = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
    current_week_start = now - timedelta(days=now.weekday())
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Получаем все задачи одним запросом с eager loading подзадач
    # Для текущей даты исключаем удаленные задачи, для прошлых дат включаем их
    is_past_date = selected_day < today
    stmt = select(models.Task).where(models.Task.user_id == user_id)
    
    # Если выбран прошлый день - показываем все задачи (включая удаленные)
    # Если выбран сегодня или будущее - показываем только не удаленные
    if not is_past_date:
        stmt = stmt.where(models.Task.deleted == False)
    
    stmt = stmt.options(joinedload(models.Task.subtasks)).order_by(models.Task.created_at.desc())
    result = db.execute(stmt)
    tasks = result.unique().scalars().all()
    
    has_changes = False
    
    # Обновляем задачи (подзадачи уже загружены)
    for task in tasks:
        # Пропускаем удаленные задачи при автоматическом переносе
        if task.deleted:
            continue
        
        # Обновляем стрик один раз для каждой задачи
        if task.last_completed_date:
            new_streak = reset_streak_if_missed(task, now)
            if new_streak != task.streak:
                task.streak = new_streak
                has_changes = True
        
        frequency = task.frequency
        
        # Ежедневные задачи - всегда переносятся на новый день (даже если выполнены)
        if frequency == 'daily':
            # Проверяем, был ли уже новый день после последнего выполнения
            if task.last_completed_date:
                last_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                if last_day < today:
                    # Ежедневные задачи всегда сбрасываются на новый день
                    task.completed = False
                    # Обновляем стрик если был пропуск
                    new_streak = reset_streak_if_missed(task, now)
                    if new_streak != task.streak:
                        task.streak = new_streak
                    has_changes = True
            elif not task.last_completed_date and task.completed:
                # Если задача выполнена, но нет last_completed_date - это странно, но сбрасываем
                task.completed = False
                has_changes = True
        
        # Еженедельные задачи - переносятся на новый день только если НЕ выполнены
        elif frequency == 'weekly':
            # Если задача не выполнена, она видна каждый день текущей недели
            # Выполненные задачи остаются выполненными до начала новой недели
            if task.completed and task.last_completed_date:
                # Выполненные еженедельные задачи переносятся только при начале новой недели
                last_week_start = task.last_completed_date - timedelta(days=task.last_completed_date.weekday())
                last_week_start = last_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                if last_week_start < current_week_start:
                    task.completed = False
                    has_changes = True
        
        # Месячные задачи - переносятся на новый день только если НЕ выполнены
        elif frequency == 'monthly':
            # Если задача не выполнена, она видна каждый день текущего месяца
            # Выполненные задачи остаются выполненными до начала нового месяца
            if task.completed and task.last_completed_date:
                # Выполненные месячные задачи переносятся только при начале нового месяца
                last_month_start = task.last_completed_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if last_month_start < current_month_start:
                    task.completed = False
                    has_changes = True
    
    # Коммитим изменения только если были изменения
    if has_changes:
        db.commit()
    
    # Фильтруем задачи по выбранной дате
    filtered_tasks = []
    for task in tasks:
        task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
        
        # Задача не может быть показана для дней до её создания
        if task_created_day and selected_day < task_created_day:
            continue
        
        # Удаленные задачи показываем только для прошлых дат
        if task.deleted and not is_past_date:
            continue
        
        frequency = task.frequency
        
        # Ежедневные задачи - показываем для всех дней после создания
        if frequency == 'daily':
            if not task_created_day or selected_day >= task_created_day:
                filtered_tasks.append(task)
        
        # Еженедельные задачи - показываем только если выбранный день в той же неделе, что и актуальная неделя задачи
        elif frequency == 'weekly':
            if task_created_day:
                # Определяем неделю выбранной даты
                selected_week_start = selected_day - timedelta(days=selected_day.weekday())
                
                # Определяем неделю создания задачи
                task_week_start = task_created_day - timedelta(days=task_created_day.weekday())
                
                # Если задача выполнена, проверяем неделю выполнения
                if task.completed and task.last_completed_date:
                    completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    completed_week_start = completed_day - timedelta(days=completed_day.weekday())
                    
                    # Показываем только если выбранный день в неделе выполнения
                    if selected_week_start == completed_week_start:
                        filtered_tasks.append(task)
                else:
                    # Невыполненная задача - показываем если выбранный день в текущей активной неделе
                    # Текущая активная неделя начинается с недели создания и продолжается до выполнения
                    if selected_week_start >= task_week_start:
                        # Проверяем, не началась ли уже следующая неделя (если это не прошлая дата)
                        if is_past_date or selected_week_start <= current_week_start:
                            filtered_tasks.append(task)
        
        # Месячные задачи - показываем только если выбранный день в том же месяце, что и актуальный месяц задачи
        elif frequency == 'monthly':
            if task_created_day:
                # Определяем месяц выбранной даты
                selected_month_start = selected_day.replace(day=1)
                
                # Определяем месяц создания задачи
                task_month_start = task_created_day.replace(day=1)
                
                # Если задача выполнена, проверяем месяц выполнения
                if task.completed and task.last_completed_date:
                    completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    completed_month_start = completed_day.replace(day=1)
                    
                    # Показываем только если выбранный день в месяце выполнения
                    if selected_month_start == completed_month_start:
                        filtered_tasks.append(task)
                else:
                    # Невыполненная задача - показываем если выбранный день в текущем активном месяце
                    # Текущий активный месяц начинается с месяца создания и продолжается до выполнения
                    if selected_month_start >= task_month_start:
                        # Проверяем, не начался ли уже следующий месяц (если это не прошлая дата)
                        if is_past_date or selected_month_start <= current_month_start:
                            filtered_tasks.append(task)
    
    return filtered_tasks


def set_task_completed(db: Session, task_id: int, user_id: int, completed: bool):
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return None
    
    completion_date = datetime.utcnow()
    
    if completed:
        task.last_completed_date = completion_date
        # Вычисляем новый стрик
        task.streak = calculate_streak_on_complete(task, completion_date)
        # Если задача повторяющаяся, обновляем следующую дату выполнения
        if task.repeat_type != models.RepeatType.NONE:
            task.next_due_date = calculate_next_due_date(task)
    else:
        # При отмене выполнения сбрасываем дату и стрик
        task.last_completed_date = None
        task.streak = 0
    
    task.completed = completed
    db.commit()
    db.refresh(task)
    # Явно загружаем подзадачи, чтобы они были включены в ответ
    _ = task.subtasks  # access relationship to load subtasks
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


def calculate_streak_on_complete(task: models.Task, completion_date: datetime = None) -> int:
    """
    Вычисляет новый стрик при выполнении задачи.
    Если задача была выполнена в предыдущем периоде - стрик продолжается, иначе сбрасывается или начинается с 1.
    """
    if completion_date is None:
        completion_date = datetime.utcnow()
    
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
        now = datetime.utcnow()
    
    # Приводим к UTC
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if task.last_completed_date.tzinfo is None:
        last_completed = task.last_completed_date.replace(tzinfo=timezone.utc)
    else:
        last_completed = task.last_completed_date
    
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





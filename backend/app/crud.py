from __future__ import annotations

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, update
from . import models
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta


def create_task(db: Session, user_id: int, title: str, description=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> models.Task:
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


def update_task(db: Session, task_id: int, user_id: int, title: str, description=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> Optional[models.Task]:
    task = get_task(db, task_id=task_id, user_id=user_id)
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
    task.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def list_tasks_with_subtasks(db: Session, user_id: int, selected_date: datetime = None):
    """
    Получает список задач с подзадачами и автоматически обновляет их состояние.
    Оптимизировано для быстрой загрузки.
    
    Args:
        selected_date: Дата для фильтрации задач (если None - используется текущая дата)
    """
    now = datetime.now(timezone.utc)
    if selected_date is None:
        selected_date = now
    
    # Подготавливаем нормализованные даты один раз (timezone-aware)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    selected_day = selected_date.replace(hour=0, minute=0, second=0, microsecond=0) if selected_date.tzinfo else selected_date.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)
    current_week_start = now - timedelta(days=now.weekday())
    current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Убеждаемся, что все даты timezone-aware
    if selected_day.tzinfo is None:
        selected_day = selected_day.replace(tzinfo=timezone.utc)
    if today.tzinfo is None:
        today = today.replace(tzinfo=timezone.utc)
    if current_week_start.tzinfo is None:
        current_week_start = current_week_start.replace(tzinfo=timezone.utc)
    if current_month_start.tzinfo is None:
        current_month_start = current_month_start.replace(tzinfo=timezone.utc)
    
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
        # Удаленные задачи не переносятся на следующий день
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
        # После 00:00 задача автоматически переносится на следующий день со статусом "невыполнена"
        if frequency == 'daily':
            # Проверяем, был ли уже новый день после последнего выполнения
            if task.last_completed_date:
                last_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Убеждаемся, что last_day timezone-aware для сравнения
                if last_day.tzinfo is None:
                    last_day = last_day.replace(tzinfo=timezone.utc)
                if last_day < today:
                    # Ежедневные задачи всегда сбрасываются на новый день
                    task.completed = False
                    # Обновляем стрик если был пропуск
                    new_streak = reset_streak_if_missed(task, now)
                    if new_streak != task.streak:
                        task.streak = new_streak
                    has_changes = True
            elif not task.last_completed_date:
                # Если задача не имеет last_completed_date, проверяем день создания
                task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
                if task_created_day:
                    if task_created_day.tzinfo is None:
                        task_created_day = task_created_day.replace(tzinfo=timezone.utc)
                    # Если задача была создана до сегодня, она должна быть невыполненной
                    if task_created_day < today:
                        task.completed = False
                        has_changes = True
                elif task.completed:
                    # Если задача выполнена, но нет last_completed_date и created_at - сбрасываем
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
                # Убеждаемся, что last_week_start timezone-aware
                if last_week_start.tzinfo is None:
                    last_week_start = last_week_start.replace(tzinfo=timezone.utc)
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
                # Убеждаемся, что last_month_start timezone-aware
                if last_month_start.tzinfo is None:
                    last_month_start = last_month_start.replace(tzinfo=timezone.utc)
                if last_month_start < current_month_start:
                    task.completed = False
                    has_changes = True
    
    # Коммитим изменения только если были изменения
    if has_changes:
        db.commit()
    
    # Фильтруем задачи по выбранной дате и устанавливаем корректный статус выполнения для выбранной даты
    filtered_tasks = []
    for task in tasks:
        task_created_day = task.created_at.replace(hour=0, minute=0, second=0, microsecond=0) if task.created_at else None
        # Убеждаемся, что task_created_day timezone-aware для сравнения
        if task_created_day and task_created_day.tzinfo is None:
            task_created_day = task_created_day.replace(tzinfo=timezone.utc)
        
        # Задача не может быть показана для дней до её создания
        if task_created_day and selected_day < task_created_day:
            continue
        
        # Удаленные задачи показываем только для прошлых дат
        # Если задача была удалена сегодня, она не должна переноситься на следующий день
        if task.deleted:
            # Показываем удаленные задачи только для прошлых дат (архив)
            if not is_past_date:
                continue
            # Для прошлых дат показываем удаленные задачи, но не обновляем их статус
        
        frequency = task.frequency
        
        # Определяем статус выполнения для выбранной даты
        task_completed_for_date = False
        
        if frequency == 'daily':
            # Ежедневные задачи - проверяем, была ли задача выполнена в выбранный день
            if task.last_completed_date:
                completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Убеждаемся, что completed_day timezone-aware для сравнения
                if completed_day.tzinfo is None:
                    completed_day = completed_day.replace(tzinfo=timezone.utc)
                # Задача выполнена только если last_completed_date совпадает с выбранным днем
                task_completed_for_date = (completed_day == selected_day)
            # Если это будущая дата - задача всегда невыполнена
            elif selected_day > today:
                task_completed_for_date = False
            # Если это сегодня или прошлая дата, используем текущий статус (после обновления выше)
            elif not is_past_date:
                task_completed_for_date = task.completed
            # Для прошлых дат без last_completed_date - задача не выполнена
            else:
                task_completed_for_date = False
        
        elif frequency == 'weekly':
            # Еженедельные задачи - проверяем, была ли задача выполнена в выбранную неделю
            if task.last_completed_date:
                completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Убеждаемся, что completed_day timezone-aware
                if completed_day.tzinfo is None:
                    completed_day = completed_day.replace(tzinfo=timezone.utc)
                completed_week_start = completed_day - timedelta(days=completed_day.weekday())
                selected_week_start = selected_day - timedelta(days=selected_day.weekday())
                # Задача выполнена только если выбранный день в той же неделе, что и выполнение
                task_completed_for_date = (selected_week_start == completed_week_start)
            elif not is_past_date:
                task_completed_for_date = task.completed
        
        elif frequency == 'monthly':
            # Месячные задачи - проверяем, была ли задача выполнена в выбранный месяц
            if task.last_completed_date:
                completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Убеждаемся, что completed_day timezone-aware
                if completed_day.tzinfo is None:
                    completed_day = completed_day.replace(tzinfo=timezone.utc)
                completed_month_start = completed_day.replace(day=1)
                selected_month_start = selected_day.replace(day=1)
                # Задача выполнена только если выбранный день в том же месяце, что и выполнение
                task_completed_for_date = (selected_month_start == completed_month_start)
            elif not is_past_date:
                task_completed_for_date = task.completed
        
        # Обновляем статус задачи для выбранной даты
        task.completed = task_completed_for_date
        
        # Для прошлых дат: если задача не выполнена для выбранной даты, все подзадачи тоже должны быть не выполнены
        # (так как мы не знаем историю выполнения подзадач по датам)
        if is_past_date and not task_completed_for_date:
            for subtask in task.subtasks:
                subtask.completed = False
        
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
                if task.last_completed_date:
                    completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    # Убеждаемся, что completed_day timezone-aware
                    if completed_day.tzinfo is None:
                        completed_day = completed_day.replace(tzinfo=timezone.utc)
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
                if task.last_completed_date:
                    completed_day = task.last_completed_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    # Убеждаемся, что completed_day timezone-aware
                    if completed_day.tzinfo is None:
                        completed_day = completed_day.replace(tzinfo=timezone.utc)
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





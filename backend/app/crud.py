from __future__ import annotations

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select, func, update
from . import models
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import logging
from .utils.date_utils import (
    normalize_to_utc,
    get_today_utc,
    normalize_date_to_utc_day,
    get_date_range_for_day,
    is_past_date as check_is_past_date
)

logger = logging.getLogger(__name__)

# Функции для работы с пользователями и часовыми поясами
def update_user_timezone(db: Session, user_id: int, timezone_offset: str):
    """Обновляет или создает запись о часовом поясе пользователя"""
    from datetime import timezone as tz
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if user:
        user.timezone_offset = timezone_offset
        user.updated_at = datetime.now(tz.utc)
    else:
        user = models.User(user_id=user_id, timezone_offset=timezone_offset)
        db.add(user)
    
    db.commit()
    db.refresh(user)
    return user

def get_user_timezone(db: Session, user_id: int) -> Optional[str]:
    """Получает часовой пояс пользователя"""
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    return user.timezone_offset if user else None

def get_all_users_with_timezone(db: Session) -> List[models.User]:
    """Получает всех пользователей с сохраненным часовым поясом"""
    return db.query(models.User).filter(models.User.timezone_offset.isnot(None)).all()

#Базовые функции для задач
def create_task(db: Session, user_id: int, title: str, description=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily') -> models.Task:
    # Преобразуем пустую строку в None для description
    if description is not None and description.strip() == '':
        description = None
    
    # Создаем задачу для текущего дня
    # Для будущих дней будут создаваться новые независимые задачи через generate_daily_tasks()
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


def get_task(db: Session, task_id: int, user_id: int) -> Optional[models.Task]:
    return db.execute(
        select(models.Task).where(models.Task.id == task_id, models.Task.user_id == user_id)
    ).scalar_one_or_none()


def update_task(db: Session, task_id: int, user_id: int, title: str, description=None, repeat_interval=1, next_due_date=None, end_date=None, category='personal', frequency='daily', current_time: datetime = None) -> Optional[models.Task]:
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


def delete_task(db: Session, task_id: int, user_id: int, current_time: datetime = None) -> bool:
    """
    Полное удаление задачи из базы данных безвозвратно.
    Удаляет задачу и все связанные подзадачи (cascade delete).
    """
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return False
    
    # Удаляем задачу из БД (подзадачи удалятся автоматически благодаря cascade)
    db.delete(task)
    db.commit()
    return True






#Работа с подзадачами
def create_subtask(db: Session, task_id: int, user_id: int, title: str) -> models.Subtask:
    parent_task = get_task(db, task_id=task_id, user_id=user_id)
    if not parent_task:
        return None

    subtask = models.Subtask(task_id=task_id, title=title)
    db.add(subtask)
    db.commit()
    db.refresh(subtask)
    return subtask


def set_subtask_completed(db: Session, subtask_id: int, user_id: int, completed: bool):
    subtask = db.execute(select(models.Subtask).where(models.Subtask.id == subtask_id)).scalar_one_or_none()
    if not subtask:
        return None
    # Проверка, что подзадача принадлежит задаче пользователя
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
    # Проверка, что подзадача принадлежит задаче пользователя
    parent_task = get_task(db, task_id=subtask.task_id, user_id=user_id)
    if not parent_task:
        return None
    subtask.title = title
    db.commit()
    db.refresh(subtask)
    return subtask


def delete_subtask(db: Session, subtask_id: int, user_id: int) -> bool:
    subtask = db.execute(select(models.Subtask).where(models.Subtask.id == subtask_id)).scalar_one_or_none()
    if not subtask:
        return False
    # Проверка, что подзадача принадлежит задаче пользователя
    parent_task = get_task(db, task_id=subtask.task_id, user_id=user_id)
    if not parent_task:
        return False
    db.delete(subtask)
    db.commit()
    return True





#Получение списка задач с подзадачами
def list_tasks_with_subtasks(db: Session, user_id: int, selected_date: datetime = None, current_time: datetime = None):
    """
    Получает список задач с подзадачами для выбранной даты.
    Работает с реальными записями в БД (каждая дата имеет свою запись).
    
    Args:
        selected_date: Дата для фильтрации задач (если None - используется текущая дата)
        current_time: Текущее время клиента (если None - используется время сервера)
    """
    # ВСЕГДА используем UTC для всех вычислений и сравнений (timezone-aware)
    today = get_today_utc(current_time)
    
    if selected_date is None:
        selected_date = normalize_to_utc(current_time) or datetime.now(timezone.utc)
    
    # Нормализуем выбранную дату в UTC (timezone-aware)
    selected_day = normalize_date_to_utc_day(selected_date)
    
    # Создаем диапазон для выбранного дня в UTC (timezone-aware)
    # Выбранный день в локальном времени клиента может охватывать 2 дня в UTC
    # Поэтому используем диапазон от начала предыдущего дня до конца следующего дня
    if selected_day:
        selected_day_start = selected_day - timedelta(days=1)
        selected_day_end = selected_day + timedelta(days=2)
    else:
        selected_day_start = None
        selected_day_end = None
    
    # Определяем, является ли выбранная дата прошлой (сравнение aware datetime)
    is_past_date = check_is_past_date(selected_day, today)
    
    # Логирование для отладки
    logger.debug(f"Filtering tasks: selected_day={selected_day}, today={today}, is_past_date={is_past_date}")
    
    # Получаем все задачи пользователя (удаленные задачи уже удалены из БД)
    stmt = select(models.Task).where(models.Task.user_id == user_id)
    
    stmt = stmt.options(selectinload(models.Task.subtasks)).order_by(models.Task.created_at.desc())
    tasks = db.scalars(stmt).all()
    
    # Фильтруем задачи по выбранной дате
    filtered_tasks = []
    for task in tasks:
        # task.created_at уже в UTC (timezone-aware), нормализуем для сравнения
        # Используем aware datetime для всех сравнений
        task_created_day = normalize_date_to_utc_day(task.created_at)
        
        frequency = task.frequency
        
        # Фильтруем задачи по дате создания (все задачи независимы)
        should_show = False
        
        if frequency == 'daily':
            # Ежедневные задачи - показываем задачи, созданные в выбранный день
            # Используем диапазон дат, так как выбранный день в локальном времени клиента
            # может охватывать 2 дня в UTC (из-за timezone offset)
            if task_created_day and selected_day_start and selected_day_end:
                # Проверяем, попадает ли дата создания задачи в диапазон выбранного дня
                if selected_day_start <= task_created_day < selected_day_end:
                    should_show = True
        
        elif frequency == 'weekly':
            # Еженедельные задачи - показываем задачи, созданные в выбранную неделю
            if task_created_day:
                selected_week_start = selected_day - timedelta(days=selected_day.weekday())
                task_week_start = task_created_day - timedelta(days=task_created_day.weekday())
                if selected_week_start == task_week_start:
                    should_show = True
        
        elif frequency == 'monthly':
            # Месячные задачи - показываем задачи, созданные в выбранный месяц
            if task_created_day:
                selected_month_start = selected_day.replace(day=1)
                task_month_start = task_created_day.replace(day=1)
                if selected_month_start == task_month_start:
                    should_show = True
        
        if should_show:
            # Статус выполнения уже установлен в поле completed при создании задачи
            # Для прошлых дат: если задача не выполнена, все подзадачи тоже должны быть не выполнены
            if is_past_date and not task.completed:
                for subtask in task.subtasks:
                    subtask.completed = False
            
            filtered_tasks.append(task)
    
    return filtered_tasks





#Выполнение задач и логика повторения/стриков
def set_task_completed(db: Session, task_id: int, user_id: int, completed: bool, current_time: datetime = None):
    task = get_task(db, task_id=task_id, user_id=user_id)
    if not task:
        return None
    
    # Используем утилиты для нормализации дат в UTC (timezone-aware)
    today = get_today_utc(current_time)
    yesterday = today - timedelta(days=1)
    
    # Нормализуем дату создания задачи в UTC для сравнения (timezone-aware)
    task_created_day = normalize_date_to_utc_day(task.created_at)
    
    # Сравниваем timezone-aware datetime
    if task_created_day is not None and yesterday is not None:
        if task_created_day < yesterday:
            # Нельзя изменять статус задач для прошлых дат (позавчера и раньше)
            raise ValueError("Cannot modify task status for past dates")
    
    # Нормализуем completion_date в UTC (timezone-aware для сохранения в БД)
    if current_time:
        completion_date = normalize_to_utc(current_time) or datetime.now(timezone.utc)
    else:
        completion_date = datetime.now(timezone.utc)
    
    if completed:
        task.last_completed_date = completion_date
        # Увеличиваем стрик при выполнении (стрик уже установлен при создании задачи)
        # Если задача еще не выполнена, стрик уже правильный (1 или больше)
        # При выполнении стрик не меняется - он уже установлен при создании на основе предыдущей задачи
        # Если задача повторяющаяся (на основе frequency), обновляем следующую дату выполнения
        if task.frequency in ('daily', 'weekly', 'monthly'):
            task.next_due_date = calculate_next_due_date(task)
    else:
        # При отмене выполнения сбрасываем дату и следующую дату выполнения
        # Стрик не сбрасываем - он остается как есть (будет использован при создании следующей задачи)
        task.last_completed_date = None
        task.next_due_date = None
    
    task.completed = completed
    db.commit()
    db.refresh(task)
    # Явно загружаем подзадачи, чтобы они были включены в ответ
    _ = task.subtasks  # access relationship to load subtasks
    return task


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
    
    # Нормализуем base_date в UTC (timezone-aware)
    base_date = normalize_to_utc(base_date)
    if base_date is None:
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
    Работает с timezone-aware datetime в UTC.
    """
    if completion_date is None:
        completion_date = datetime.now(timezone.utc)
    
    # Нормализуем completion_date в UTC (timezone-aware)
    completion_date = normalize_to_utc(completion_date) or datetime.now(timezone.utc)
    completion_day = normalize_date_to_utc_day(completion_date)
    
    frequency = task.frequency
    
    # Используем старый last_completed_date для проверки непрерывности
    # (до того как мы обновим его в set_task_completed)
    old_last_completed = task.last_completed_date
    
    # Если это первое выполнение - стрик = 1
    if not old_last_completed:
        return 1
    
    # Нормализуем last_completed в UTC (timezone-aware)
    last_completed = normalize_to_utc(old_last_completed)
    if last_completed is None:
        return 1
    
    last_day = normalize_date_to_utc_day(last_completed)
    if last_day is None or completion_day is None:
        return 1
    
    # Для daily - проверяем последовательность дней
    if frequency == 'daily':
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
        last_week_start = last_day - timedelta(days=last_day.weekday())
        completion_week_start = completion_day - timedelta(days=completion_day.weekday())
        
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
        last_month_start = last_day.replace(day=1)
        completion_month_start = completion_day.replace(day=1)
        
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
    Работает с timezone-aware datetime в UTC.
    """
    if not task.last_completed_date:
        return 0
    
    # Нормализуем now в UTC (timezone-aware)
    if now is None:
        now = datetime.now(timezone.utc)
    else:
        now = normalize_to_utc(now) or datetime.now(timezone.utc)
    
    # Нормализуем last_completed в UTC (timezone-aware)
    last_completed = normalize_to_utc(task.last_completed_date)
    if last_completed is None:
        return 0
    
    frequency = task.frequency
    
    # Нормализуем даты до начала дня (timezone-aware)
    last_day = normalize_date_to_utc_day(last_completed)
    today = normalize_date_to_utc_day(now)
    
    if last_day is None or today is None:
        return task.streak
    
    # Для daily - проверяем пропуск дня
    if frequency == 'daily':
        # Если последнее выполнение было больше чем вчера - сбрасываем стрик
        days_diff = (today - last_day).days
        if days_diff > 1:
            return 0  # Сброс стрика
        
        return task.streak
    
    # Для weekly - проверяем пропуск недели
    elif frequency == 'weekly':
        last_week_start = last_day - timedelta(days=last_day.weekday())
        current_week_start = today - timedelta(days=today.weekday())
        
        # Если последнее выполнение было больше чем неделю назад - сбрасываем стрик
        weeks_diff = (current_week_start - last_week_start).days // 7
        if weeks_diff > 1:
            return 0  # Сброс стрика
        
        return task.streak
    
    # Для monthly - проверяем пропуск месяца
    elif frequency == 'monthly':
        last_month_start = last_day.replace(day=1)
        current_month_start = today.replace(day=1)
        
        # Если последнее выполнение было больше чем месяц назад - сбрасываем стрик
        months_diff = (current_month_start.year - last_month_start.year) * 12 + (current_month_start.month - last_month_start.month)
        if months_diff > 1:
            return 0  # Сброс стрика
        
        return task.streak
    
    return task.streak






#Статистика 
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
    # Используем timezone-aware datetime в UTC
    now = datetime.now(timezone.utc)
    today = normalize_date_to_utc_day(now)
    
    if today is None:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Определяем период фильтрации (timezone-aware)
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
        models.Task.user_id == user_id
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
                # Нормализуем дату выполнения в UTC (timezone-aware)
                completed_date = normalize_date_to_utc_day(task_last_completed)
                
                if completed_date is None:
                    continue
                
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
                # Нормализуем дату создания в UTC (timezone-aware)
                task_created_day = normalize_date_to_utc_day(task_created)
                
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






#Работа с заметками
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


def get_notes_by_month(db: Session, user_id: int, year: int, month: int):
    """
    Получает все заметки за указанный месяц.
    Возвращает словарь {date: note} для быстрого доступа.
    """
    from datetime import date as date_class
    # Создаем диапазон дат для месяца
    start_date = date_class(year, month, 1)
    if month == 12:
        end_date = date_class(year + 1, 1, 1)
    else:
        end_date = date_class(year, month + 1, 1)
    
    notes = db.execute(
        select(models.Note)
        .where(
            models.Note.user_id == user_id,
            models.Note.date >= start_date.strftime('%Y-%m-%d'),
            models.Note.date < end_date.strftime('%Y-%m-%d')
        )
        .order_by(models.Note.date.desc(), models.Note.created_at.desc())
    ).scalars().all()
    
    # Группируем по датам, берем первую (самую новую) заметку для каждой даты
    notes_by_date = {}
    for note in notes:
        if note.date not in notes_by_date:
            notes_by_date[note.date] = note
    
    return notes_by_date


def delete_note(db: Session, note_id: int, user_id: int) -> bool:
    note = db.execute(
        select(models.Note).where(models.Note.id == note_id, models.Note.user_id == user_id)
    ).scalar_one_or_none()
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True






#Автоматическая генерация задач на следующий день
def generate_daily_tasks(db: Session, target_date: datetime = None, user_id: Optional[int] = None):
    """
    Генерирует задачи для нового дня.
    В 00:00 10 ноября создает задачи для 10 ноября на основе задач 9 ноября.
    
    Логика:
    - Находит все задачи из предыдущего дня (кроме удаленных)
    - Создает новые задачи для нового дня с created_at = новый день
    - Копирует все подзадачи со статусом "не выполнено"
    
    Args:
        target_date: Дата, для которой нужно создать задачи (по умолчанию - сегодня)
        user_id: ID пользователя, для которого создавать задачи (если None - для всех пользователей)
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc)
    
    # Нормализуем даты в UTC (timezone-aware)
    target_date = normalize_to_utc(target_date) or datetime.now(timezone.utc)
    target_date = normalize_date_to_utc_day(target_date) or target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    prev_date = target_date - timedelta(days=1)
    
    # Создаем диапазоны для сравнения с timezone-aware полями в БД
    # Ищем все задачи, у которых created_at попадает в диапазон предыдущего дня
    # Например, для 10 ноября ищем задачи с created_at от 00:00 9 ноября до 00:00 10 ноября
    prev_date_start = prev_date
    prev_date_end = prev_date + timedelta(days=1)
    
    # Для проверки существующих задач
    target_date_start = target_date
    target_date_end = target_date + timedelta(days=1)
    
    logger.info(f"🔄 Generating tasks for {target_date.date()}, looking for tasks from {prev_date.date()}")
    if user_id:
        logger.info(f"   For user_id: {user_id}")
    logger.info(f"   Date range: {prev_date_start} <= created_at < {prev_date_end}")
    
    created_count = 0
    
    # Получаем список пользователей для обработки
    if user_id:
        # Обрабатываем только указанного пользователя
        all_user_ids = [user_id]
    else:
        # Получаем все пользователи, у которых есть задачи
        all_user_ids = db.execute(
            select(models.Task.user_id).distinct()
        ).scalars().all()
    
    if not all_user_ids:
        logger.info("⚠️ No users with tasks found")
        return 0
    
    logger.info(f"📋 Found {len(all_user_ids)} users with tasks")
    
    for user_id in all_user_ids:
        # Ищем все задачи предыдущего дня
        # Используем диапазон дат для правильного сравнения с timezone-aware полями
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
            logger.info(f"  User {user_id}: No tasks found from {prev_date.date()}")
            continue
        
        logger.info(f"  User {user_id}: Found {len(source_tasks)} tasks from {prev_date.date()}")
        
        # Для каждой найденной задачи создаем новую задачу
        for source_task in source_tasks:
            # Проверяем, не истекла ли задача (сравнение timezone-aware datetime)
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
                    models.Task.title == source_task.title,  # Ищем по названию
                    models.Task.created_at >= target_date_start,
                    models.Task.created_at < target_date_end
                )
            ).scalar_one_or_none()
            
            if existing_task:
                logger.debug(f"    Task '{source_task.title}' already exists for {target_date.date()}, skipping")
                continue  # Задача уже создана для этого дня
            
            # Определяем стрик на основе предыдущей задачи:
            # - Если предыдущая задача была выполнена (completed = True): стрик = предыдущий_стрик + 1
            # - Если не выполнена (completed = False): стрик = 0
            new_streak = 0
            if source_task.completed:
                # Задача была выполнена 9 ноября, увеличиваем стрик для задачи 10 ноября
                new_streak = source_task.streak + 1

            else:
                logger.debug(f"    Task '{source_task.title}' was not completed, streak reset to 0")
            
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
                streak=new_streak,  # Устанавливаем стрик на основе предыдущей задачи
                deleted=False
            )
            # Устанавливаем created_at в UTC (timezone-aware) для сохранения в БД
            # target_date уже нормализован в UTC (timezone-aware)
            new_task.created_at = target_date
            db.add(new_task)
            # Делаем flush, чтобы задача получила ID перед созданием подзадач
            db.flush()
            created_count += 1
            
            # Копируем подзадачи со статусом "не выполнено"
            subtasks_count = 0
            for subtask in source_task.subtasks:
                new_subtask = models.Subtask(
                    task_id=new_task.id,  # Теперь new_task.id уже не None
                    title=subtask.title,
                    completed=False
                )
                # Устанавливаем created_at в UTC (timezone-aware)
                new_subtask.created_at = target_date
                db.add(new_subtask)
                subtasks_count += 1
            
            if subtasks_count > 0:
                logger.debug(f"Created {subtasks_count} subtasks for task {new_task.id}")
    
    if created_count > 0:
        db.commit()
        logger.info(f"✅ Created {created_count} tasks for {target_date.date()}")
    
    return created_count





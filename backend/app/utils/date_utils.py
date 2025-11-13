"""
Утилиты для работы с датами и временем
Все операции выполняются в UTC
"""
from datetime import datetime, timedelta, timezone
from typing import Optional


def normalize_to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Нормализует datetime в UTC и возвращает как naive datetime.
    
    Args:
        dt: datetime объект (может быть timezone-aware или naive)
        
    Returns:
        naive datetime в UTC или None
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Если naive, считаем что это уже UTC
        return dt
    
    # Конвертируем в UTC и делаем naive
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def get_today_utc(current_time: Optional[datetime] = None) -> datetime:
    """
    Получает начало сегодняшнего дня в UTC.
    
    Args:
        current_time: Текущее время (если None - используется datetime.now(timezone.utc))
        
    Returns:
        naive datetime начала дня в UTC
    """
    if current_time is None:
        now = datetime.now(timezone.utc)
    else:
        now = normalize_to_utc(current_time) or datetime.now(timezone.utc)
    
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def normalize_date_to_utc_day(date: Optional[datetime]) -> Optional[datetime]:
    """
    Нормализует дату в UTC и возвращает начало дня как naive datetime.
    
    Args:
        date: datetime объект
        
    Returns:
        naive datetime начала дня в UTC или None
    """
    if date is None:
        return None
    
    normalized = normalize_to_utc(date)
    if normalized is None:
        return None
    
    return normalized.replace(hour=0, minute=0, second=0, microsecond=0)


def get_date_range_for_day(day: datetime) -> tuple[datetime, datetime]:
    """
    Получает диапазон дат для дня (начало и конец дня в UTC).
    Используется для фильтрации задач, созданных в определенный день.
    
    Args:
        day: datetime начала дня (может быть в любом timezone)
        
    Returns:
        tuple (start, end) - начало и конец дня в UTC (naive)
    """
    day_start = normalize_date_to_utc_day(day)
    if day_start is None:
        raise ValueError("Invalid day")
    
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def is_past_date(selected_day: Optional[datetime], today: Optional[datetime] = None) -> bool:
    """
    Проверяет, является ли выбранная дата прошлой.
    
    Args:
        selected_day: Выбранная дата
        today: Сегодняшняя дата (если None - вычисляется автоматически)
        
    Returns:
        True если selected_day < today, иначе False
    """
    if selected_day is None:
        return False
    
    if today is None:
        today = get_today_utc()
    
    selected_normalized = normalize_date_to_utc_day(selected_day)
    today_normalized = normalize_date_to_utc_day(today)
    
    if selected_normalized is None or today_normalized is None:
        return False
    
    # Сравниваем даты (без времени)
    return selected_normalized.date() < today_normalized.date()


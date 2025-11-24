"""
Зависимости (dependencies) для FastAPI endpoints
"""
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from .database import get_db
from .telegram_auth import parse_and_validate_init_data

logger = logging.getLogger(__name__)


def get_client_time(header_client_time: str = Header(None, alias="X-Client-Time")) -> datetime:
    """
    Получает локальное время клиента из заголовка запроса и конвертирует в UTC.
    Клиент отправляет локальное время в ISO формате с timezone offset (например: 2024-11-09T10:30:00.000+03:00).
    Если заголовок не передан, используем UTC.
    """
    if header_client_time:
        try:
            # Парсим ISO формат времени от клиента (локальное время с timezone offset)
            client_time = datetime.fromisoformat(header_client_time.replace('Z', '+00:00'))
            
            # Если время имеет timezone, конвертируем в UTC
            if client_time.tzinfo:
                # Конвертируем локальное время клиента в UTC
                client_time_utc = client_time.astimezone(timezone.utc)
                # Возвращаем как naive datetime в UTC (для совместимости с остальным кодом)
                return client_time_utc.replace(tzinfo=None)
            # Если timezone нет, считаем что это уже UTC
            return client_time
        except (ValueError, AttributeError) as e:
            logger.debug(f"Не удалось распарсить время клиента: {e}")
            pass
    # Если заголовок не передан или невалидный - используем UTC
    return datetime.now(timezone.utc)


def get_client_timezone(header_client_time: str = Header(None, alias="X-Client-Time")):
    """
    Получает timezone offset клиента из заголовка запроса.
    Возвращает timezone объект или None если не удалось определить.
    """
    if header_client_time:
        try:
            client_time = datetime.fromisoformat(header_client_time.replace('Z', '+00:00'))
            if client_time.tzinfo:
                return client_time.tzinfo
        except (ValueError, AttributeError):
            pass
    return None


def get_user_id(x_telegram_init_data: str | None = Header(default=None)) -> int:
    """
    Извлекает и валидирует user_id из Telegram init data
    """
    if not x_telegram_init_data:
        logger.warning("⚠️  Отсутствует заголовок X-Telegram-Init-Data")
        raise HTTPException(status_code=401, detail="Missing Telegram init data")
    
    user = parse_and_validate_init_data(x_telegram_init_data)
    if not user or "id" not in user:
        logger.warning("❌ Не удалось валидировать Telegram auth данные")
        raise HTTPException(status_code=401, detail="Invalid Telegram auth")
    
    user_id = int(user["id"])
    logger.debug(f"✅ Пользователь аутентифицирован: user_id={user_id}")
    return user_id


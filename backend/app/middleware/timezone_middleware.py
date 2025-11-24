"""
Middleware для автоматического сохранения часового пояса пользователя
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from datetime import datetime
import logging

from ..telegram_auth import parse_and_validate_init_data
from ..repositories.user_repository import UserRepository
from ..database import get_db

logger = logging.getLogger(__name__)


class TimezoneMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматического сохранения часового пояса пользователя"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Сохраняем часовой пояс только для аутентифицированных запросов
        if "X-Telegram-Init-Data" in request.headers:
            try:
                user = parse_and_validate_init_data(request.headers.get("X-Telegram-Init-Data"))
                if user and "id" in user:
                    user_id = int(user["id"])
                    client_time_header = request.headers.get("X-Client-Time")
                    
                    if client_time_header:
                        try:
                            client_time = datetime.fromisoformat(client_time_header.replace('Z', '+00:00'))
                            if client_time.tzinfo:
                                # Извлекаем offset в формате "+03:00"
                                offset = client_time.strftime("%z")
                                if offset:
                                    # Форматируем как "+03:00"
                                    offset_formatted = f"{offset[:3]}:{offset[3:]}"
                                    db = next(get_db())
                                    try:
                                        UserRepository.update_timezone(db, user_id, offset_formatted)
                                    except Exception as e:
                                        logger.debug(f"Не удалось сохранить часовой пояс для пользователя {user_id}: {e}")
                                    finally:
                                        db.close()
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Не удалось распарсить время клиента: {e}")
            except Exception as e:
                logger.debug(f"Не удалось сохранить часовой пояс: {e}")
        
        return response


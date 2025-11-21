"""Модуль для отправки уведомлений пользователям"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List
from types import SimpleNamespace
from aiogram import Bot
import logging

from db_utils import get_all_users_with_timezone

logger = logging.getLogger(__name__)


async def send_notification(bot: Bot, user_id: int, message: str):
    """Отправляет уведомление пользователю"""
    try:
        await bot.send_message(chat_id=user_id, text=message)
        logger.debug(f"📤 Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        # Пользователь мог заблокировать бота или удалить чат
        logger.debug(f"⚠️  Не удалось отправить уведомление пользователю {user_id}: {str(e)[:50]}")


def parse_timezone_offset(offset_str: str) -> float:
    """Парсит строку часового пояса в число часов"""
    if not offset_str:
        return 0.0
    
    sign = 1 if offset_str[0] == '+' else -1
    hours = int(offset_str[1:3])
    minutes = int(offset_str[4:6]) if len(offset_str) > 4 else 0
    return sign * (hours + minutes / 60)


async def send_notifications_job(bot: Bot, target_hour: int, message: str):
    """Отправляет уведомления всем пользователям, у которых наступило указанное время"""
    try:
        # Получаем текущее время в UTC
        now_utc = datetime.now(timezone.utc)
        
        # Получаем всех пользователей
        try:
            users = get_all_users_with_timezone()
        except Exception as db_error:
            logger.error(f"❌ Ошибка базы данных при получении пользователей: {db_error}")
            return
        
        if not users:
            logger.debug("⏭️  Пользователи не найдены")
            return
        
        sent_count = 0
        checked_count = 0
        
        for user in users:
            if not user.timezone_offset:
                continue
            
            try:
                # Парсим часовой пояс
                offset_hours = parse_timezone_offset(user.timezone_offset)
                user_tz = timezone(timedelta(hours=offset_hours))
                
                # Вычисляем текущее время в часовом поясе пользователя
                now_user_tz = now_utc.astimezone(user_tz)
                user_hour = now_user_tz.hour
                user_minute = now_user_tz.minute
                checked_count += 1
                
                # Проверяем, что наступило нужное время (в пределах первых 5 минут часа)
                if user_hour == target_hour and user_minute < 5:
                    await send_notification(bot, user.user_id, message)
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Ошибка обработки пользователя {user.user_id}: {e}")
                continue
        
        if sent_count > 0:
            time_label = "утренние" if target_hour == 9 else "вечерние"
            logger.info(f"📨 Отправлено {sent_count} {time_label} уведомлений (проверено {checked_count} пользователей)")
        else:
            logger.debug(f"⏭️  Уведомления не отправлены (проверено {checked_count} пользователей, ни у кого не {target_hour}:00)")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в задаче уведомлений: {e}")


async def send_evening_notifications(bot: Bot):
    """Отправляет вечерние уведомления в 22:00"""
    await send_notifications_job(bot, 22, "Пора отметить выполненные задачи")


async def send_morning_notifications(bot: Bot):
    """Отправляет утренние уведомления в 9:00"""
    await send_notifications_job(bot, 9, "Хорошего дня!")


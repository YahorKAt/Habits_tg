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
        logger.info(f"✅ Sent notification to user {user_id}: {message[:50]}...")
    except Exception as e:
        # Пользователь мог заблокировать бота или удалить чат
        logger.warning(f"⚠️ Failed to send notification to user {user_id}: {e}")


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
        users = get_all_users_with_timezone()
        
        if not users:
            logger.debug("No users found for notifications")
            return
        
        sent_count = 0
        
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
                
                # Если наступило нужное время
                if user_hour == target_hour:
                    await send_notification(bot, user.user_id, message)
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing user {user.user_id} for notifications: {e}", exc_info=True)
                continue
        
        if sent_count > 0:
            logger.info(f"📨 Sent {sent_count} notifications ({message[:30]}...)")
        else:
            logger.debug(f"⏭️  No notifications sent (checked {len(users)} users, none at {target_hour}:00)")
            
    except Exception as e:
        logger.error(f"❌ Error in notifications job: {e}", exc_info=True)


async def send_evening_notifications(bot: Bot):
    """Отправляет вечерние уведомления в 22:00"""
    await send_notifications_job(bot, 22, "Пора отметить выполненные задачи")


async def send_morning_notifications(bot: Bot):
    """Отправляет утренние уведомления в 9:00"""
    await send_notifications_job(bot, 9, "Хорошего дня!")


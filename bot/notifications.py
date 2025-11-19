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
        logger.info(f"🕐 Running notifications job at {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')} for target hour {target_hour}:00")
        
        # Получаем всех пользователей
        users = get_all_users_with_timezone()
        
        if not users:
            logger.warning("⚠️ No users found for notifications")
            return
        
        logger.info(f"👥 Found {len(users)} users to check")
        
        sent_count = 0
        checked_count = 0
        
        for user in users:
            if not user.timezone_offset:
                logger.debug(f"⏭️  User {user.user_id} has no timezone_offset, skipping")
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
                
                logger.debug(f"👤 User {user.user_id}: timezone={user.timezone_offset}, local time={now_user_tz.strftime('%H:%M')}, hour={user_hour}")
                
                # Проверяем, что наступило нужное время (в пределах первых 5 минут часа)
                # Это позволяет отправлять уведомления даже если задача запустилась с небольшой задержкой
                if user_hour == target_hour and user_minute < 5:
                    logger.info(f"✅ Sending notification to user {user.user_id} (local time: {now_user_tz.strftime('%H:%M')})")
                    await send_notification(bot, user.user_id, message)
                    sent_count += 1
                elif user_hour == target_hour:
                    logger.debug(f"⏭️  User {user.user_id} is at {target_hour}:{user_minute:02d}, but minute > 5, skipping")
                    
            except Exception as e:
                logger.error(f"❌ Error processing user {user.user_id} for notifications: {e}", exc_info=True)
                continue
        
        if sent_count > 0:
            logger.info(f"📨 Sent {sent_count} notifications out of {checked_count} checked users ({message[:30]}...)")
        else:
            logger.info(f"⏭️  No notifications sent (checked {checked_count} users, none at {target_hour}:00-{target_hour}:05)")
            
    except Exception as e:
        logger.error(f"❌ Error in notifications job: {e}", exc_info=True)


async def send_evening_notifications(bot: Bot):
    """Отправляет вечерние уведомления в 22:00"""
    await send_notifications_job(bot, 22, "Пора отметить выполненные задачи")


async def send_morning_notifications(bot: Bot):
    """Отправляет утренние уведомления в 9:00"""
    await send_notifications_job(bot, 9, "Хорошего дня!")


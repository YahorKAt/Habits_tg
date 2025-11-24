"""
Обработчики команд бота
"""
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import logging

from config import WEBAPP_URL
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики команд"""
    
    @dp.message_handler(commands=["start"])
    async def start(message: types.Message):
        """Обработчик команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username or "без имени"
        logger.info(f"📥 Получена команда /start от пользователя {user_id} (@{username})")
        
        if not WEBAPP_URL:
            logger.error(f"❌ WEBAPP_URL не настроен для пользователя {user_id}")
            await message.answer("ERROR: WEBAPP_URL is not configured. Please set it in environment variables.")
            return
        
        logger.info(f"🔗 Отправка кнопки Mini App пользователю {user_id} (URL: {WEBAPP_URL})")
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton(text="Open Habits Mini App", web_app=WebAppInfo(url=WEBAPP_URL)))
        await message.answer("Open the Habits Mini App:", reply_markup=kb)
        logger.info(f"✅ Команда /start успешно обработана для пользователя {user_id}")
    
    @dp.message_handler(commands=["test_notification"])
    async def test_notification(message: types.Message, bot: Bot):
        """Тестовая команда для проверки отправки уведомлений"""
        user_id = message.from_user.id
        username = message.from_user.username or "без имени"
        logger.info(f"📥 Получена команда /test_notification от пользователя {user_id} (@{username})")
        
        try:
            logger.info(f"📤 Попытка отправить тестовое уведомление пользователю {user_id}...")
            await bot.send_message(chat_id=user_id, text="🧪 Тестовое уведомление работает!")
            logger.info(f"✅ Тестовое уведомление успешно отправлено пользователю {user_id}")
            await message.answer("✅ Тестовое уведомление отправлено!")
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке тестового уведомления пользователю {user_id}: {e}")
            await message.answer(f"❌ Ошибка отправки уведомления: {e}")
    
    @dp.message_handler(commands=["check_timezone"])
    async def check_timezone(message: types.Message):
        """Проверяет часовой пояс пользователя"""
        from repositories.user_repository import UserRepository
        from services.notification_service import parse_timezone_offset
        from datetime import datetime, timezone, timedelta
        
        user_id = message.from_user.id
        username = message.from_user.username or "без имени"
        logger.info(f"📥 Получена команда /check_timezone от пользователя {user_id} (@{username})")
        
        logger.info(f"🔍 Поиск информации о часовом поясе для пользователя {user_id}...")
        users = UserRepository.get_all_with_timezone()
        logger.info(f"📊 Найдено {len(users)} пользователей с часовым поясом в базе данных")
        
        user = next((u for u in users if u.user_id == user_id), None)
        
        if user and user.timezone_offset:
            logger.info(f"✅ Найден часовой пояс для пользователя {user_id}: {user.timezone_offset}")
            # Вычисляем текущее время пользователя
            offset_hours = parse_timezone_offset(user.timezone_offset)
            user_tz = timezone(timedelta(hours=offset_hours))
            now_utc = datetime.now(timezone.utc)
            now_user_tz = now_utc.astimezone(user_tz)
            
            logger.info(f"🕐 Время пользователя {user_id}: UTC={now_utc.strftime('%H:%M:%S')}, локальное={now_user_tz.strftime('%H:%M:%S')}")
            
            response = (
                f"📍 Ваш часовой пояс: {user.timezone_offset}\n"
                f"🕐 Текущее время (UTC): {now_utc.strftime('%H:%M:%S')}\n"
                f"🕐 Ваше локальное время: {now_user_tz.strftime('%H:%M:%S')}\n"
                f"📅 Уведомления приходят в:\n"
                f"   • 9:00 (утро)\n"
                f"   • 22:00 (вечер)"
            )
        else:
            logger.warning(f"⚠️  Часовой пояс не найден для пользователя {user_id}")
            response = (
                f"⚠️ Часовой пояс не сохранен в базе данных.\n"
                f"Откройте Mini App, чтобы сохранить часовой пояс."
            )
        
        await message.answer(response)
        logger.info(f"✅ Команда /check_timezone успешно обработана для пользователя {user_id}")


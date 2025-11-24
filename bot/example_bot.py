"""
Главный файл бота
"""
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BOT_TOKEN
from handlers.commands import register_handlers
from services.notification_service import NotificationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Отключаем лишние логи
logging.getLogger('aiogram').setLevel(logging.WARNING)
logging.getLogger('apscheduler').setLevel(logging.WARNING)
logging.getLogger('aiogram.dispatcher').setLevel(logging.WARNING)
logging.getLogger('aiogram.bot').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Регистрация обработчиков
register_handlers(dp)


async def run_evening_notifications():
    """Обертка для запуска вечерних уведомлений"""
    await NotificationService.send_evening_notifications(bot)


async def run_morning_notifications():
    """Обертка для запуска утренних уведомлений"""
    await NotificationService.send_morning_notifications(bot)


async def on_startup(_):
    """Вызывается при запуске бота"""
    # Настраиваем планировщик для отправки уведомлений
    # Уведомления запускаются каждый час в 00 минут
    # Внутри функции проверяется, для каких пользователей наступило нужное время
    
    # Вечерние уведомления (22:00 по времени пользователя)
    scheduler.add_job(
        run_evening_notifications,
        trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
        id='evening_notifications',
        name='Send evening notifications at 22:00 user time',
        replace_existing=True,
        misfire_grace_time=60  # Разрешаем задержку до 60 секунд
    )
    
    # Утренние уведомления (9:00 по времени пользователя)
    scheduler.add_job(
        run_morning_notifications,
        trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
        id='morning_notifications',
        name='Send morning notifications at 9:00 user time',
        replace_existing=True,
        misfire_grace_time=60  # Разрешаем задержку до 60 секунд
    )
    
    scheduler.start()
    logger.info("✅ Планировщик уведомлений запущен")


async def on_shutdown(_):
    """Вызывается при остановке бота"""
    logger.info("🛑 Остановка планировщика...")
    scheduler.shutdown(wait=True)
    logger.info("✅ Планировщик остановлен")


if __name__ == "__main__":
    logger.info("🚀 Запуск бота...")
    
    # Создаем event loop если его нет
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # Запускаем бота с callbacks для startup и shutdown
        executor.start_polling(
            dp,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
    except KeyboardInterrupt:
        logger.info("🛑 Остановка бота...")
        if scheduler.running:
            scheduler.shutdown(wait=True)
        logger.info("✅ Бот остановлен")

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
logger.info("📝 Регистрация обработчиков команд...")
register_handlers(dp)
logger.info("✅ Обработчики команд зарегистрированы")


async def run_evening_notifications():
    """Обертка для запуска вечерних уведомлений"""
    logger.info("🌙 Запуск задачи отправки вечерних уведомлений...")
    await NotificationService.send_evening_notifications(bot)
    logger.info("✅ Задача вечерних уведомлений завершена")


async def run_morning_notifications():
    """Обертка для запуска утренних уведомлений"""
    logger.info("🌅 Запуск задачи отправки утренних уведомлений...")
    await NotificationService.send_morning_notifications(bot)
    logger.info("✅ Задача утренних уведомлений завершена")


async def on_startup(_):
    """Вызывается при запуске бота"""
    logger.info("⚙️  Инициализация планировщика уведомлений...")
    
    # Настраиваем планировщик для отправки уведомлений
    # Уведомления запускаются каждый час в 00 минут
    # Внутри функции проверяется, для каких пользователей наступило нужное время
    
    # Вечерние уведомления (22:00 по времени пользователя)
    logger.info("📅 Регистрация задачи вечерних уведомлений (22:00 по времени пользователя)...")
    scheduler.add_job(
        run_evening_notifications,
        trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
        id='evening_notifications',
        name='Send evening notifications at 22:00 user time',
        replace_existing=True,
        misfire_grace_time=60  # Разрешаем задержку до 60 секунд
    )
    logger.info("✅ Задача вечерних уведомлений зарегистрирована")
    
    # Утренние уведомления (9:00 по времени пользователя)
    logger.info("📅 Регистрация задачи утренних уведомлений (9:00 по времени пользователя)...")
    scheduler.add_job(
        run_morning_notifications,
        trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
        id='morning_notifications',
        name='Send morning notifications at 9:00 user time',
        replace_existing=True,
        misfire_grace_time=60  # Разрешаем задержку до 60 секунд
    )
    logger.info("✅ Задача утренних уведомлений зарегистрирована")
    
    scheduler.start()
    logger.info("✅ Планировщик уведомлений успешно запущен и готов к работе")


async def on_shutdown(_):
    """Вызывается при остановке бота"""
    logger.info("🛑 Начало остановки планировщика уведомлений...")
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("✅ Планировщик уведомлений успешно остановлен")
    else:
        logger.info("ℹ️  Планировщик уже был остановлен")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("🚀 Начало запуска Telegram бота...")
    logger.info("=" * 60)
    
    # Создаем event loop если его нет
    try:
        loop = asyncio.get_event_loop()
        logger.info("✅ Event loop получен")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("✅ Новый event loop создан")
    
    try:
        logger.info("🔄 Запуск бота в режиме polling...")
        # Запускаем бота с callbacks для startup и shutdown
        executor.start_polling(
            dp,
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
    except KeyboardInterrupt:
        logger.info("=" * 60)
        logger.info("🛑 Получен сигнал остановки (KeyboardInterrupt)...")
        logger.info("=" * 60)
        if scheduler.running:
            logger.info("⏹️  Остановка планировщика...")
            scheduler.shutdown(wait=True)
            logger.info("✅ Планировщик остановлен")
        logger.info("✅ Бот успешно остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при работе бота: {e}", exc_info=True)
        if scheduler.running:
            logger.info("⏹️  Принудительная остановка планировщика...")
            scheduler.shutdown(wait=False)
        raise

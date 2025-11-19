from dotenv import load_dotenv
load_dotenv()
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import logging

from notifications import send_evening_notifications, send_morning_notifications

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()  # Убираем пробелы если они есть

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN environment variable is not set!")
    print("Please set it like: set BOT_TOKEN=your_bot_token_here")
    exit(1)

print(f"Using bot token: {BOT_TOKEN[:10]}...")
if WEBAPP_URL:
    print(f"WebApp URL: {WEBAPP_URL}")
else:
    print("WARNING: WEBAPP_URL is not set!")

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()


@dp.message_handler(commands=["start"]) 
async def start(message: types.Message):
    if not WEBAPP_URL:
        await message.answer("ERROR: WEBAPP_URL is not configured. Please set it in environment variables.")
        return
    
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(text="Open Habits Mini App", web_app=WebAppInfo(url=WEBAPP_URL)))
    await message.answer("Open the Habits Mini App:", reply_markup=kb)


async def run_evening_notifications():
    """Обертка для запуска вечерних уведомлений"""
    await send_evening_notifications(bot)


async def run_morning_notifications():
    """Обертка для запуска утренних уведомлений"""
    await send_morning_notifications(bot)


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
        replace_existing=True
    )
    
    # Утренние уведомления (9:00 по времени пользователя)
    scheduler.add_job(
        run_morning_notifications,
        trigger=CronTrigger(minute=0),  # Каждый час в 00 минут
        id='morning_notifications',
        name='Send morning notifications at 9:00 user time',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Notification scheduler started")


async def on_shutdown(_):
    """Вызывается при остановке бота"""
    logger.info("Stopping scheduler...")
    scheduler.shutdown(wait=True)
    logger.info("✅ Scheduler stopped")


if __name__ == "__main__":
    print("Starting bot...")
    
    try:
        # Запускаем бота с callbacks для startup и shutdown
        executor.start_polling(
            dp, 
            skip_updates=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown
        )
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        if scheduler.running:
            scheduler.shutdown(wait=True)
        logger.info("✅ Bot stopped")





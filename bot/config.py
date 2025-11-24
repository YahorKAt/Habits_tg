"""
Конфигурация бота
"""
import os
import logging

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "").strip()

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не установлен в переменных окружения!")
    raise ValueError("BOT_TOKEN is required")

logger.info(f"🤖 Bot token: {BOT_TOKEN[:10]}...")
if WEBAPP_URL:
    logger.info(f"🌐 WebApp URL: {WEBAPP_URL}")
else:
    logger.warning("⚠️  WEBAPP_URL is not set!")


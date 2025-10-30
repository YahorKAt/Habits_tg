from dotenv import load_dotenv
load_dotenv()

import json
import os

from typing import Dict, Any, Optional
import logging

from telegram_webapp_auth.auth import TelegramAuthenticator
logger = logging.getLogger(__name__)

def parse_and_validate_init_data(init_data_raw: str) -> Optional[Dict[str, Any]]:
    """
    Валидация init_data только через библиотеку telegram-webapp-auth.
    """
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        logger.error("BOT_TOKEN not found")
        return None

    try:
        from telegram_webapp_auth import TelegramWebAppAuth  # type: ignore
        auth = TelegramAuthenticator(bot_token)
        valid = auth.validate(init_data_raw)
        user_raw = valid.get("user") if isinstance(valid, dict) else None
        if isinstance(user_raw, dict):
            return user_raw
        if isinstance(user_raw, str):
            try:
                return json.loads(user_raw)
            except Exception:
                return None
        return None
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return None

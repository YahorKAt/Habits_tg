from dotenv import load_dotenv
load_dotenv()

import urllib.parse
import hashlib
import hmac
import json
import time
import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def parse_and_validate_init_data(init_data_raw: str) -> Optional[Dict[str, Any]]:
    """
    Валидация init_data от Telegram WebApp.
    Используем оригинальные URL-encoded значения для проверки hash.
    """
    try:
        # Разбираем на пары key=value
        parsed_data = {}
        hash_value = None
        
        for item in init_data_raw.split('&'):
            if '=' not in item:
                continue
            
            key, value = item.split('=', 1)
            key_decoded = urllib.parse.unquote_plus(key)
            value_decoded = urllib.parse.unquote_plus(value)
            
            if key_decoded == "hash":
                hash_value = value_decoded
                continue
            
            if key_decoded == "signature":
                continue
            
            # Сохраняем декодированные значения
            parsed_data[key_decoded] = value_decoded

        if not hash_value:
            logger.warning("Missing hash in init_data")
            return None

        # Проверяем auth_date
        auth_date_str = parsed_data.get("auth_date")
        if auth_date_str:
            try:
                auth_date = int(auth_date_str)
                current_time = int(time.time())
                if current_time - auth_date > 86400:
                    logger.warning(f"Init data expired")
                    return None
            except (ValueError, TypeError):
                logger.warning(f"Invalid auth_date")
                return None

        # Получаем BOT_TOKEN
        bot_token = os.getenv("BOT_TOKEN", "")
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return None

        # Формируем data_check_string: key=value отсортированные по key
        # По документации Telegram используются ДЕКОДИРОВАННЫЕ значения
        data_check_string = "\n".join(
            f"{key}={parsed_data[key]}" 
            for key in sorted(parsed_data.keys())
        )

        # secret_key = HMAC-SHA256(key="WebAppData", msg=bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Вычисляем hash
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        logger.info(f"=== Telegram Auth Debug ===")
        logger.info(f"data_check_string:\n{data_check_string}")
        logger.info(f"Expected: {hash_value}")
        logger.info(f"Computed: {computed_hash}")
        logger.info(f"BOT_TOKEN (first 20): {bot_token[:20]}")

        # Сравниваем
        if computed_hash != hash_value:
            logger.error("❌ Hash mismatch!")
            logger.error(f"Проверьте что BOT_TOKEN на Render = {bot_token}")
            return None

        logger.info("✅ Hash matched!")

        # Извлекаем user
        user_raw = parsed_data.get("user")
        if not user_raw:
            logger.warning("Missing user")
            return None

        try:
            user_data = json.loads(user_raw)
            logger.info(f"✅ User validated: {user_data.get('id')}")
            return user_data
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None

    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return None

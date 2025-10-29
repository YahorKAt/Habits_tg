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
    Используем ОРИГИНАЛЬНЫЕ URL-encoded значения для формирования data_check_string.
    """
    logger.info(f"=== Starting init_data validation ===")
    logger.info(f"Raw init_data (first 200 chars): {init_data_raw[:200]}")
    
    try:
        # Разбираем на пары key=value
        # Для data_check_string нужны ОРИГИНАЛЬНЫЕ значения (URL-encoded)
        # Для использования нужны ДЕКОДИРОВАННЫЕ значения
        data_for_check = {}  # key -> original_value (URL-encoded)
        data_decoded = {}    # key -> decoded_value
        hash_value = None
        
        for item in init_data_raw.split('&'):
            if '=' not in item:
                continue
            
            key_encoded, value_encoded = item.split('=', 1)
            key = urllib.parse.unquote_plus(key_encoded)
            value_decoded = urllib.parse.unquote_plus(value_encoded)
            
            if key == "hash":
                hash_value = value_decoded
                continue
            
            if key == "signature":
                continue
            
            # Сохраняем оригинальное URL-encoded значение для проверки
            data_for_check[key] = value_encoded
            # Сохраняем декодированное для использования
            data_decoded[key] = value_decoded

        if not hash_value:
            logger.warning("Missing hash in init_data")
            return None

        # Проверяем auth_date
        auth_date_str = data_decoded.get("auth_date")
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
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return None
        
        logger.info(f"BOT_TOKEN from env: {bot_token}")

        # Формируем data_check_string из ОРИГИНАЛЬНЫХ URL-encoded значений
        # key=value (где value остаётся URL-encoded)
        data_check_string = "\n".join(
            f"{key}={data_for_check[key]}" 
            for key in sorted(data_for_check.keys())
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

        # Извлекаем user из ДЕКОДИРОВАННЫХ данных
        user_raw = data_decoded.get("user")
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

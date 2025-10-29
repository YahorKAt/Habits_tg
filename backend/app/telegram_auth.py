from dotenv import load_dotenv
load_dotenv()

import hmac
import hashlib
import urllib.parse
import os
import json
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def parse_and_validate_init_data(init_data_raw: str) -> Optional[Dict[str, Any]]:
    """
    Валидация init_data от Telegram WebApp согласно официальной документации.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # ВАЖНО: Парсим вручную, сохраняя значения в URL-encoded виде
        # parse_qs автоматически декодирует значения, что ломает проверку hash!
        data_raw = {}  # Храним значения как есть (URL-encoded)
        data_decoded = {}  # Декодированные значения для использования
        
        for pair in init_data_raw.split('&'):
            if '=' not in pair:
                continue
            key_raw, value_raw = pair.split('=', 1)
            # Декодируем ключ для использования
            key = urllib.parse.unquote_plus(key_raw)
            # Сохраняем оригинальное значение для проверки hash
            data_raw[key] = value_raw
            # Декодируем значение для использования
            data_decoded[key] = urllib.parse.unquote_plus(value_raw)

        # Извлекаем hash для проверки
        hash_value = data_raw.pop("hash", None)
        if not hash_value:
            logger.warning("Missing hash in init_data")
            return None

        # Удаляем signature если есть (он не должен быть в строке для проверки)
        data_raw.pop("signature", None)
        data_decoded.pop("signature", None)

        # Проверяем auth_date (данные не должны быть старше 24 часов)
        auth_date_str = data_decoded.get("auth_date")
        if auth_date_str:
            try:
                auth_date = int(auth_date_str)
                current_time = int(time.time())
                if current_time - auth_date > 86400:  # 24 часа в секундах
                    logger.warning(f"Init data expired. auth_date: {auth_date}, current: {current_time}")
                    return None
            except (ValueError, TypeError):
                logger.warning(f"Invalid auth_date format: {auth_date_str}")
                return None

        # Получаем BOT_TOKEN из окружения
        bot_token = os.getenv("BOT_TOKEN", "")
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return None

        # Собираем строку для проверки: используем ИСХОДНЫЕ URL-encoded значения!
        # Это критично - hash вычисляется на основе закодированных значений
        check_data = "\n".join(f"{k}={data_raw[k]}" for k in sorted(data_raw.keys()))
        
        # Вычисляем secret_key и hash
        secret_key = hashlib.sha256(f"WebAppData{bot_token}".encode()).digest()
        computed_hash = hmac.new(secret_key, check_data.encode(), hashlib.sha256).hexdigest()
        
        logger.info(f"init_data_raw length: {len(init_data_raw)}")
        logger.info(f"BOT_TOKEN length: {len(bot_token)}")
        logger.info(f"check_data (first 200 chars): {check_data[:200]}...")
        # Сравниваем hash
        if computed_hash != hash_value:
            logger.warning(f"Hash mismatch! Expected: {hash_value}, Got: {computed_hash}")
            logger.info(f"check_data full: {check_data}")
            logger.info(f"data keys: {list(data_raw.keys())}")
            return None

        # Извлекаем user из JSON (используем декодированные данные)
        user_raw = data_decoded.get("user")
        if not user_raw:
            logger.warning("Missing user in init_data")
            return None

        try:
            user_data = json.loads(user_raw)
            logger.info(f"Successfully validated init_data for user_id: {user_data.get('id')}")
            return user_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse user JSON: {e}")
            return None

    except Exception as e:
        logger.error(f"Error validating init_data: {e}", exc_info=True)
        return None





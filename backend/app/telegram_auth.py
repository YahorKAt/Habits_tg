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


def normalize_slashes(s: str) -> str:
    """Заменяет экранированные слэши \/ на обычные /"""
    return s.replace('\\/', '/')


def parse_and_validate_init_data(init_data_raw: str) -> Optional[Dict[str, Any]]:
    """
    Валидация init_data от Telegram WebApp.
    Пробуем заменить экранированные слеши \/ на / для совпадения hash.
    """
    try:
        # Парсим initData
        data = urllib.parse.parse_qs(init_data_raw, keep_blank_values=True)
        data = {k: v[0] for k, v in data.items()}

        # Извлекаем hash
        hash_value = data.pop("hash", None)
        if not hash_value:
            logger.warning("Missing hash in init_data")
            return None
        
        # Удаляем signature если есть
        data.pop("signature", None)

        # Заменяем экранированные слэши в JSON полях
        for k, v in data.items():
            if v.startswith("{") and v.endswith("}"):
                data[k] = normalize_slashes(v)

        # Проверяем auth_date
        auth_date_str = data.get("auth_date")
        if auth_date_str:
            try:
                auth_date = int(auth_date_str)
                current_time = int(time.time())
                if current_time - auth_date > 86400:
                    logger.warning(f"Init data expired. auth_date: {auth_date}, current: {current_time}")
                    return None
            except (ValueError, TypeError):
                logger.warning(f"Invalid auth_date format: {auth_date_str}")
                return None

        # Собираем check_data
        check_data = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))

        # Получаем BOT_TOKEN
        bot_token = os.getenv("BOT_TOKEN", "")
        if not bot_token:
            logger.error("BOT_TOKEN not found in environment variables")
            return None

        # Вычисляем secret_key = HMAC-SHA256(key="WebAppData", msg=bot_token)
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=bot_token.encode(),
            digestmod=hashlib.sha256
        ).digest()

        # Вычисляем hash
        computed_hash = hmac.new(secret_key, check_data.encode(), hashlib.sha256).hexdigest()

        # Логирование
        logger.info(f"=== Telegram Auth (with slash normalization) ===")
        logger.info(f"check_data:\n{check_data}")
        logger.info(f"Expected hash: {hash_value}")
        logger.info(f"Computed hash: {computed_hash}")

        # Сравниваем хэши
        if not hmac.compare_digest(computed_hash, hash_value):
            logger.error("❌ Hash mismatch!")
            return None

        logger.info("✅ Hash validation passed!")

        # Извлекаем user из JSON
        user_raw = data.get("user")
        if not user_raw:
            logger.warning("Missing user in init_data")
            return None

        try:
            user_data = json.loads(user_raw)
            logger.info(f"✅ Successfully validated init_data for user_id: {user_data.get('id')}")
            return user_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse user JSON: {e}")
            return None

    except Exception as e:
        logger.error(f"Error validating init_data: {e}", exc_info=True)
        return None

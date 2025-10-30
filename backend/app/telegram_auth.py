from dotenv import load_dotenv
load_dotenv()

from urllib.parse import parse_qs
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
        # 1) Попытка валидации через официальную библиотеку telegram-webapp-auth
        #    https://github.com/swimmwatch/telegram-webapp-auth (v3.0.6)
        #    Если библиотека недоступна/бросит исключение – ниже сработает надёжный фолбэк.
        from telegram_webapp_auth import TelegramWebAppAuth  # type: ignore
        try:
            bot_token_env = os.getenv("BOT_TOKEN", "").strip()
            if bot_token_env:
                auth = TelegramWebAppAuth(bot_token_env)
                valid = auth.validate(init_data_raw)
                user_raw = valid.get("user") if isinstance(valid, dict) else None
                if isinstance(user_raw, dict):
                    logger.info("✅ User validated via telegram-webapp-auth")
                    return user_raw
                if isinstance(user_raw, str):
                    try:
                        logger.info("✅ User validated via telegram-webapp-auth (JSON string)")
                        return json.loads(user_raw)
                    except Exception:
                        pass
        except Exception as _:
            # Переходим на фолбэк-реализацию ниже
            pass

        # 2) Фолбэк‑валидация (ручная, совместимая с Telegram docs)
        # Разбираем на пары key=value используя parse_qs
        parsed_data = parse_qs(init_data_raw)
        parsed_data = {k: v[0] for k, v in parsed_data.items()}
        
        # Извлекаем hash
        hash_value = parsed_data.pop("hash", None)

        if not hash_value:
            logger.warning("Missing hash in init_data")
            return None
        
        # Удаляем signature если есть
        parsed_data.pop("signature", None)
        
        # Убираем экранированные слеши из JSON полей
        for key, value in parsed_data.items():
            if value.startswith("{") or value.startswith("["):
                # Это JSON - убираем \/ → /
                parsed_data[key] = value.replace("\\/", "/")

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
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return None
        
        logger.info(f"BOT_TOKEN from env: {bot_token}")

        # Формируем data_check_string из ДЕКОДИРОВАННЫХ значений
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

        # Сравниваем
        if computed_hash != hash_value:
            logger.error("❌ Hash mismatch!")
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

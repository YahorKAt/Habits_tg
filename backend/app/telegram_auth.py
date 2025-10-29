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
    Валидация init_data от Telegram WebApp согласно официальной документации:
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        # Разбираем init_data_raw на параметры
        # Сохраняем оригинальные пары key=value для формирования data_check_string
        
        raw_pairs = []  # Оригинальные пары "key=value" как строки
        parsed_data = {}  # Декодированные данные для использования
        hash_value = None
        
        for pair in init_data_raw.split('&'):
            if '=' not in pair:
                continue
            
            key, value = pair.split('=', 1)
            key_decoded = urllib.parse.unquote_plus(key)
            
            # Проверяем hash и signature
            if key_decoded == "hash":
                hash_value = urllib.parse.unquote_plus(value)
                continue
            
            if key_decoded == "signature":
                continue
            
            # Сохраняем ОРИГИНАЛЬНУЮ пару key=value (как строку!)
            raw_pairs.append((key_decoded, pair))  # (decoded_key, "key=value")
            
            # Сохраняем декодированные данные для использования
            parsed_data[key_decoded] = urllib.parse.unquote_plus(value)
        
        if not hash_value:
            logger.warning("Missing hash in init_data")
            return None
        
        # Проверяем auth_date (данные не должны быть старше 24 часов)
        auth_date_str = parsed_data.get("auth_date")
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

        # Формируем data_check_string: сортируем по ключам, используем ОРИГИНАЛЬНЫЕ пары
        # Сортируем по декодированному ключу, но берем оригинальную строку "key=value"
        pairs_sorted = sorted(raw_pairs, key=lambda x: x[0])
        check_data = "\n".join(pair[1] for pair in pairs_sorted)
        
        # ВАЖНО: Вычисляем secret_key используя HMAC, а не SHA256!
        # secret_key = HMAC-SHA256(key="WebAppData", message=bot_token)
        secret_key = hmac.new(
            key=b"WebAppData", 
            msg=bot_token.encode(), 
            digestmod=hashlib.sha256
        ).digest()
        
        # Вычисляем hash от check_data
        computed_hash = hmac.new(secret_key, check_data.encode(), hashlib.sha256).hexdigest()
        
        logger.info(f"init_data_raw length: {len(init_data_raw)}")
        logger.info(f"BOT_TOKEN exists: {bool(bot_token)}, length: {len(bot_token) if bot_token else 0}")
        logger.info(f"check_data length: {len(check_data)}")
        logger.info(f"check_data repr: {repr(check_data[:200])}")  # Показываем специальные символы
        logger.info(f"parsed_data keys: {sorted(parsed_data.keys())}")
        
        # ВРЕМЕННАЯ ОТЛАДКА: пропустить проверку hash
        skip_hash_check = os.getenv("SKIP_HASH_CHECK", "false").lower() == "true"
        
        # Сравниваем hash
        if computed_hash != hash_value:
            logger.warning(f"Hash mismatch!")
            logger.warning(f"Expected hash: {hash_value}")
            logger.warning(f"Computed hash: {computed_hash}")
            logger.info(f"check_data repr full: {repr(check_data)}")
            logger.info(f"BOT_TOKEN (first 50): {bot_token[:50] if len(bot_token) > 50 else bot_token}")
            logger.info(f"BOT_TOKEN full length: {len(bot_token)}")
            
            # Дополнительная диагностика
            logger.info(f"Number of \\n in check_data: {check_data.count(chr(10))}")
            logger.info(f"parsed_data items: {list(parsed_data.items())}")
            
            if not skip_hash_check:
                return None
            else:
                logger.warning("⚠️ SKIPPING HASH CHECK (SKIP_HASH_CHECK=true) - FOR DEBUGGING ONLY!")
        else:
            logger.info("✅ Hash validation passed!")

        # Извлекаем user из JSON (используем декодированные данные)
        user_raw = parsed_data.get("user")
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





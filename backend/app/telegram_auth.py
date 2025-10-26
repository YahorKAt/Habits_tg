import hmac
import hashlib
import urllib.parse
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def parse_and_validate_init_data(init_data_raw: str) -> Optional[Dict[str, Any]]:
    # According to Telegram WebApp auth docs
    # init_data is URL-encoded key=value pairs joined by '&'
    try:
        data = urllib.parse.parse_qs(init_data_raw, keep_blank_values=True)
        data = {k: v[0] for k, v in data.items()}
    except Exception as e:
        logger.error(f"Failed to parse init data: {e}")
        return None

    hash_value = data.pop("hash", None)
    if not hash_value:
        logger.warning("Hash not found in init data")
        return None

    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        logger.warning("BOT_TOKEN not set in environment")
        return None

    check_data = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, check_data.encode(), hashlib.sha256).hexdigest()
    
    if computed_hash != hash_value:
        logger.warning(f"Hash validation failed. Expected: {hash_value}, Got: {computed_hash}")
        return None

    # Extract user JSON
    import json

    user_raw = data.get("user")
    if not user_raw:
        logger.warning("User data not found in init data")
        return None
    try:
        user_data = json.loads(user_raw)
        logger.info(f"Successfully validated Telegram auth for user: {user_data.get('id', 'unknown')}")
        return user_data
    except Exception as e:
        logger.error(f"Failed to parse user JSON: {e}")
        return None





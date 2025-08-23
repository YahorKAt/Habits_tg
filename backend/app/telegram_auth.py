import hmac
import hashlib
import urllib.parse
import os
from typing import Dict, Any, Optional


def parse_and_validate_init_data(init_data_raw: str) -> Optional[Dict[str, Any]]:
    # According to Telegram WebApp auth docs
    # init_data is URL-encoded key=value pairs joined by '&'
    data = urllib.parse.parse_qs(init_data_raw, keep_blank_values=True)
    data = {k: v[0] for k, v in data.items()}

    hash_value = data.pop("hash", None)
    if not hash_value:
        return None

    bot_token = os.getenv("BOT_TOKEN", "")
    if not bot_token:
        return None

    check_data = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    computed_hash = hmac.new(secret_key, check_data.encode(), hashlib.sha256).hexdigest()
    if computed_hash != hash_value:
        return None

    # Extract user JSON
    import json

    user_raw = data.get("user")
    if not user_raw:
        return None
    try:
        return json.loads(user_raw)
    except Exception:
        return None





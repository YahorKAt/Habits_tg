


import hashlib
import hmac
import urllib.parse

bot_token = "8294461897:AAGmR53gKOlz1-O8c-1aDRh6prSoLIrS0TQ"
init_data_raw = "query_id=AAHy-W0UAAAAAPL5bRRGtG7F&user=%7B%22id%22%3A342751730%2C%22first_name%22%3A%22Y%D0%B0h%D0%BEr%22%2C%22last_name%22%3A%22%22%2C%22username%22%3A%22Yahokatk%22%2C%22language_code%22%3A%22ru%22%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2FUiA8VM51nMA8563YFrJWiT70BnA1fZdCGvoaG2vGF0k.svg%22%7D&auth_date=1761680273&signature=9w1G5frxyJGbMeTO50WfVPob9S4jFraNPpFy1jG1FCzWOa6qfNAxg1Std9CAOkKIip47OQ_621PBT4p5q4mnCg&hash=5188143e66c25853aad82db32fefc8999e22ea8a04813830abad29d5ca858745"

# --- Парсим параметры ---
data = urllib.parse.parse_qs(init_data_raw, keep_blank_values=True)
data = {k: v[0] for k, v in data.items()}

hash_value = data.pop("hash")
data.pop("signature", None)  # важно

# --- Собираем строку для проверки ---
check_data = "\n".join(f"{k}={data[k]}" for k in sorted(data.keys()))

# --- Считаем подпись ---
secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
computed_hash = hmac.new(secret_key, check_data.encode("utf-8"), hashlib.sha256).hexdigest()

# --- Выводим для отладки ---
print("check_data:\n", check_data)
print("\nTelegram hash:", hash_value)
print("Computed hash:", computed_hash)
print("\n✅ Совпадает:", computed_hash == hash_value)

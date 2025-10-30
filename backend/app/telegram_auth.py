import hashlib
import hmac
import json
import logging
import os
import typing
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from json import JSONDecodeError
from urllib.parse import parse_qs
from urllib.parse import unquote

from telegram_webapp_auth.data import WebAppChat
from telegram_webapp_auth.data import WebAppInitData
from telegram_webapp_auth.data import WebAppUser

logger = logging.getLogger(__name__)


class BaseTWAError(Exception):
    """Base class for all TWA-related exceptions."""
    pass


class InvalidInitDataError(BaseTWAError):
    """Raised when the init data is invalid."""
    pass


class ExpiredInitDataError(BaseTWAError):
    """Raised when the init data has expired."""
    pass


def generate_secret_key(token: str) -> bytes:
    """Generates a secret key from a Telegram token.

    Links:
        https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    Args:
        token: Telegram Bot Token

    Returns:
        bytes: secret key
    """
    base = "WebAppData".encode("utf-8")
    token_enc = token.encode("utf-8")
    return hmac.digest(base, token_enc, hashlib.sha256)


class TelegramAuthenticator:
    """Telegram Web App Authenticator."""

    def __init__(self, secret: bytes) -> None:
        """Initialize the authenticator with a secret key.

        Args:
            secret: secret key generated from the Telegram Bot Token
        """
        self._secret = secret

    @staticmethod
    def __parse_init_data(data: str) -> dict:
        """Convert init_data string into dictionary.

        Args:
            data: the query string passed by the webapp
        """
        if not data:
            raise InvalidInitDataError("Init Data cannot be empty")
        parsed_data = parse_qs(data)
        return {key: value[0] for key, value in parsed_data.items()}

    @staticmethod
    def __parse_json(data: str) -> dict:
        """Convert JSON string value from WebAppInitData to Python dictionary.

        Links:
            https://core.telegram.org/bots/webapps#webappinitdata

        Raises:
            InvalidInitDataError
        """
        try:
            return json.loads(unquote(data))
        except JSONDecodeError:
            raise InvalidInitDataError("Cannot decode init data")

    def _validate(self, hash_: str, init_data: str) -> bool:
        """Validates the data received from the Telegram web app, using the method from Telegram documentation.

        Links:
            https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Args:
            hash_: hash from init data
            init_data: init data from webapp

        Returns:
            bool: Validation result
        """
        init_data_bytes = init_data.encode("utf-8")
        client_hash = hmac.new(self._secret, init_data_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(client_hash, hash_)

    @staticmethod
    def _check_expiry(auth_date: typing.Optional[str], expr_in: typing.Optional[timedelta]):
        """Check if the auth_date is present and not expired."""
        if not auth_date:
            raise InvalidInitDataError("Init data does not contain auth_date")
        try:
            auth_dt = datetime.fromtimestamp(float(auth_date), tz=timezone.utc)
        except ValueError:
            raise InvalidInitDataError("Invalid auth_date")
        if expr_in:
            now = datetime.now(tz=timezone.utc)
            if now - auth_dt > expr_in:
                raise ExpiredInitDataError

    def __serialize_init_data(self, init_data_dict: typing.Dict[str, typing.Any]) -> WebAppInitData:
        """Serialize the init data dictionary into WebAppInitData object.

        Args:
            init_data_dict: the init data dictionary

        Returns:
            WebAppInitData: the serialized WebAppInitData object
        """
        user_data = init_data_dict.get("user")
        if user_data:
            user_data = self.__parse_json(user_data)
            init_data_dict["user"] = WebAppUser(**user_data)
        else:
            init_data_dict["user"] = None

        chat_data = init_data_dict.get("chat")
        if chat_data:
            chat_data = self.__parse_json(chat_data)
            init_data_dict["chat"] = WebAppChat(**chat_data)
        else:
            init_data_dict["chat"] = None

        receiver_data = init_data_dict.get("receiver")
        if receiver_data:
            receiver_data = self.__parse_json(receiver_data)
            init_data_dict["receiver"] = WebAppUser(**receiver_data)
        else:
            init_data_dict["receiver"] = None

        return WebAppInitData(**init_data_dict)

    def validate(self, init_data: str, expr_in: typing.Optional[timedelta] = None) -> WebAppInitData:
        """Validates the data received via the Mini App. Returns a parsed init data object if is valid.

        Links:
            https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

        Args:
            init_data: init data from mini app
            expr_in: time delta to check if the token is expired

        Returns:
            WebAppInitData: parsed init a data object

        Raises:
            InvalidInitDataError: if the init data is invalid
            ExpiredInitDataError: if the init data is expired
        """
        init_data = unquote(init_data)
        init_data_dict = self.__parse_init_data(init_data)
        data_check_string = "\n".join(
            f"{key}={val}"
            for key, val in sorted(init_data_dict.items(), key=lambda item: item[0])
            if key != "hash"
        )
        hash_ = init_data_dict.get("hash")
        if not hash_:
            raise InvalidInitDataError("Init data does not contain hash")
        auth_date = init_data_dict.get("auth_date")
        self._check_expiry(auth_date, expr_in)
        hash_ = hash_.strip()
        if not self._validate(hash_, data_check_string):
            raise InvalidInitDataError("Invalid data")
        return self.__serialize_init_data(init_data_dict)


def parse_and_validate_init_data(init_data_raw: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    """Validate Telegram init data and return user dict on success.

    Uses BOT_TOKEN from environment to generate the secret. Returns None on failure.
    """
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        logger.error("BOT_TOKEN not found")
        return None

    try:
        secret = generate_secret_key(bot_token)
        auth = TelegramAuthenticator(secret)
        # Optional expiry check; adjust as needed
        init_obj = auth.validate(init_data_raw, expr_in=timedelta(days=1))

        user_obj = getattr(init_obj, "user", None)
        if user_obj is None:
            return None

        # Try common serialization methods across dataclass/pydantic/custom objects
        if hasattr(user_obj, "dict") and callable(getattr(user_obj, "dict")):
            user_dict = user_obj.dict()
        elif hasattr(user_obj, "model_dump") and callable(getattr(user_obj, "model_dump")):
            user_dict = user_obj.model_dump()
        elif hasattr(user_obj, "__dict__"):
            user_dict = {k: v for k, v in user_obj.__dict__.items() if not k.startswith("_")}
        else:
            # Fallback minimal payload
            user_id = getattr(user_obj, "id", None)
            if user_id is None:
                return None
            user_dict = {"id": user_id}

        # Ensure id is present and int
        if "id" not in user_dict:
            user_id = getattr(user_obj, "id", None)
            if user_id is None:
                return None
            user_dict["id"] = user_id

        try:
            user_dict["id"] = int(user_dict["id"])  # type: ignore[index]
        except Exception:
            return None

        return user_dict
    except ExpiredInitDataError:
        logger.warning("Telegram init data expired")
        return None
    except InvalidInitDataError as e:
        logger.error(f"Invalid Telegram init data: {e}")
        return None
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return None

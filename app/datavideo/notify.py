import os
from typing import Any, Callable

import requests
from loguru import logger

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT_SECONDS = 20


def send_alert(text: str, post: Callable[..., Any] = requests.post) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not set")
        return False
    try:
        response = post(url=_TELEGRAM_URL.format(token=token), json={"chat_id": chat_id, "text": text}, timeout=_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        logger.warning(f"telegram alert failed: {type(error).__name__}")
        return False
    return bool(getattr(response, "ok", False))

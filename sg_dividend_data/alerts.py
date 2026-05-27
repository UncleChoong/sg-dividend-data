"""Telegram failure alerts. No-op if env vars missing."""
from __future__ import annotations
import os
import requests


def telegram_alert(message: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": chat, "text": message[:4000]}, timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        return False

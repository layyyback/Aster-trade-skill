#!/usr/bin/env python3
"""Shared utilities for Aster volume monitor: API client + Telegram push."""

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

DEFAULT_BASE_URL = "https://fapi.asterdex.com"


class AsterMarketClient:
    """Public-only GET client for Aster Futures."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()


class TelegramNotifier:
    """Send messages via Telegram Bot API."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send(self, text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
        resp = requests.post(
            self.api_url,
            json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
            timeout=15,
        )
        return resp.json()


def get_tg_notifier() -> Optional[TelegramNotifier]:
    """Build notifier from env vars; return None if not configured."""
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TG_CHAT_ID", "").strip()
    if token and chat_id:
        return TelegramNotifier(token, chat_id)
    return None


def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def format_number(n: float) -> str:
    """Format number with comma separators."""
    if n >= 1:
        return f"{n:,.2f}"
    return f"{n:.6f}"


def output_json(data: Any) -> int:
    print(json.dumps(data, ensure_ascii=False))
    return 0


def output_error(exc: Exception) -> int:
    print(json.dumps({"error": str(exc)}, ensure_ascii=False))
    return 1

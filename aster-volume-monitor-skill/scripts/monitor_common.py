#!/usr/bin/env python3
"""Shared utilities for Aster volume monitor: API client + output helpers."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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

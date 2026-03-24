#!/usr/bin/env python3
"""Shared utilities for Aster Futures market data scripts."""

import json
import sys
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "https://fapi.asterdex.com"


class AsterMarketClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()


def output_json(data: Any) -> int:
    print(json.dumps(data, ensure_ascii=False))
    return 0


def output_error(exc: Exception) -> int:
    print(json.dumps({"error": str(exc)}, ensure_ascii=False))
    return 1


def add_base_url_arg(parser) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)

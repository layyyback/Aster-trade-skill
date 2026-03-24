#!/usr/bin/env python3
"""Shared utilities for Aster Futures V1 signed endpoints."""

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Tuple
from urllib.parse import urlencode

import requests

ALLOWED_ENV_KEYS = {
    "ASTER_API_KEY",
    "ASTER_SECRET_KEY",
    "ASTER_USER",
    "ASTER_SIGNER",
    "ASTER_SIGNER_PRIVATE_KEY",
}


def load_env_file(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            if key not in ALLOWED_ENV_KEYS:
                continue
            value = val.strip().strip("'").strip('"')
            # Do not override existing runtime credentials with empty file values.
            if value == "":
                continue
            os.environ[key] = value


def require_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise ValueError(f"Missing required env var: {name}")
    return v


def format_exchange_response(status_code: int, body: Any) -> Dict[str, Any]:
    return {"status_code": status_code, "body": body}


class AsterV1Client:
    def __init__(self, base_url: str, api_key: str, secret_key: str, recv_window: int):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key
        self.recv_window = recv_window
        self.session = requests.Session()

    def _signed_params(self, params: Dict[str, Any]) -> Dict[str, str]:
        p = {k: str(v) for k, v in params.items() if v is not None}
        p["recvWindow"] = str(self.recv_window)
        p["timestamp"] = str(int(time.time() * 1000))
        qs = urlencode(p)
        sig = hmac.new(self.secret_key.encode("utf-8"), qs.encode("utf-8"), hashlib.sha256).hexdigest()
        p["signature"] = sig
        return p

    def signed_request(self, method: str, path: str, params: Dict[str, Any]) -> Tuple[int, Any]:
        url = f"{self.base_url}{path}"
        headers = {"X-MBX-APIKEY": self.api_key}
        signed = self._signed_params(params)
        method_upper = method.upper()
        if method_upper == "GET":
            resp = self.session.get(url, params=signed, headers=headers, timeout=20)
        elif method_upper == "POST":
            resp = self.session.post(url, data=signed, headers=headers, timeout=20)
        elif method_upper == "DELETE":
            resp = self.session.delete(url, params=signed, headers=headers, timeout=20)
        else:
            raise ValueError(f"Unsupported method: {method}")
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text}
        return resp.status_code, body

    def public_get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self.session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

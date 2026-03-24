#!/usr/bin/env python3
"""Shared utilities for Aster Futures V3 scripts."""

import json
import math
import os
import time
from typing import Any, Dict, Tuple

import requests
from eth_abi import encode
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import keccak

ALLOWED_ENV_KEYS = {
    "ASTER_USER",
    "ASTER_SIGNER",
    "ASTER_SIGNER_PRIVATE_KEY",
    "ASTER_API_KEY",
    "ASTER_SECRET_KEY",
}

ERROR_HINTS = {
    -1000: "General exchange-side failure. Check API wallet binding, signature inputs, and endpoint path.",
    -1102: "Missing or malformed parameter. Check required fields and parameter formats.",
    -2019: "Insufficient margin. Transfer collateral or reduce order size.",
    -1021: "Timestamp outside recvWindow. Check local clock and lower latency.",
}


def _normalize_value(value: Any) -> str:
    """Normalize values for deterministic signature payload serialization."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def load_env_file(path: str) -> None:
    """Load only allowed keys from env file."""
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
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env var: {name}")
    return value


def format_exchange_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Build response with optional hint for common errors."""
    payload: Dict[str, Any] = {"status_code": status_code, "body": body}
    if isinstance(body, dict) and "code" in body:
        code = body.get("code")
        try:
            code_int = int(code)
        except Exception:
            code_int = None
        if code_int in ERROR_HINTS:
            payload["hint"] = ERROR_HINTS[code_int]
    return payload


def compact_order_fields(order: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "orderId",
        "symbol",
        "status",
        "side",
        "positionSide",
        "type",
        "avgPrice",
        "origQty",
        "executedQty",
        "cumQuote",
        "time",
        "updateTime",
    ]
    return {k: order.get(k) for k in keys if k in order}


def compact_balance_fields(entry: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "asset",
        "availableBalance",
        "crossWalletBalance",
        "crossUnPnl",
        "marginAvailable",
        "updateTime",
    ]
    return {k: entry.get(k) for k in keys if k in entry}


class AsterV3Client:
    def __init__(self, base_url: str, user: str, signer: str, private_key: str, recv_window: int):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.signer = signer
        self.private_key = private_key
        self.recv_window = recv_window
        self.session = requests.Session()

    def _sign_payload(self, params: Dict[str, Any]) -> Dict[str, str]:
        payload = {k: _normalize_value(v) for k, v in params.items() if v is not None}
        payload["recvWindow"] = str(self.recv_window)
        payload["timestamp"] = str(int(time.time() * 1000))

        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        nonce = math.trunc(time.time() * 1_000_000)

        digest = keccak(
            encode(
                ["string", "address", "address", "uint256"],
                [raw, self.user, self.signer, nonce],
            )
        ).hex()

        signature = "0x" + Account.sign_message(
            encode_defunct(hexstr=digest), private_key=self.private_key
        ).signature.hex()

        payload["nonce"] = str(nonce)
        payload["user"] = self.user
        payload["signer"] = self.signer
        payload["signature"] = signature
        return payload

    def signed_request(self, method: str, path: str, params: Dict[str, Any]) -> Tuple[int, Any]:
        url = f"{self.base_url}{path}"
        signed = self._sign_payload(params)
        method_upper = method.upper()
        if method_upper == "GET":
            resp = self.session.get(url, params=signed, timeout=20)
        elif method_upper == "POST":
            resp = self.session.post(url, data=signed, timeout=20)
        elif method_upper == "DELETE":
            resp = self.session.delete(url, data=signed, timeout=20)
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

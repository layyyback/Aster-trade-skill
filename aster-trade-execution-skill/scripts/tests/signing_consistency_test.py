#!/usr/bin/env python3
"""Fixture-based checks for V3 signing normalization consistency."""

import json
import os
import sys

from eth_abi import encode
from eth_utils import keccak

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from v3_common import _normalize_value


FIXTURE_USER = "0x7bAe340Ee4D5182eB2B81d60C29B838Ee7BC512C"
FIXTURE_SIGNER = "0x4B926C74B415cEba1b704aA192b46e60a7983ab4"
FIXTURE_NONCE = 1700000000123456
FIXTURE_TIMESTAMP = "1700000000000"
FIXTURE_RECV_WINDOW = "5000"

EXPECTED_RAW = (
    '{"meta":"{\\"a\\":2,\\"b\\":1}","quantity":"0.001","recvWindow":"5000",'
    '"reduceOnly":"false","symbol":"BTCUSDT","tags":"[\\"x\\",{\\"k\\":\\"v\\"}]",'
    '"timestamp":"1700000000000","type":"MARKET"}'
)
EXPECTED_DIGEST_HEX = "a1ef644df4d4e664b37554c2b219d3bf93fb1f9af32413cdab5b62ae9098379a"


def build_raw_payload(params: dict) -> str:
    payload = {k: _normalize_value(v) for k, v in params.items() if v is not None}
    payload["recvWindow"] = FIXTURE_RECV_WINDOW
    payload["timestamp"] = FIXTURE_TIMESTAMP
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def build_digest(raw: str) -> str:
    encoded = encode(
        ["string", "address", "address", "uint256"],
        [raw, FIXTURE_USER, FIXTURE_SIGNER, FIXTURE_NONCE],
    )
    return keccak(encoded).hex()


def main() -> int:
    params = {
        "symbol": "BTCUSDT",
        "type": "MARKET",
        "reduceOnly": False,
        "meta": {"a": 2, "b": 1},
        "tags": ["x", {"k": "v"}],
        "quantity": "0.001",
    }

    raw = build_raw_payload(params)
    digest = build_digest(raw)

    if raw != EXPECTED_RAW:
        print(json.dumps({"error": "raw_mismatch", "got": raw, "expected": EXPECTED_RAW}, ensure_ascii=False))
        return 1
    if digest != EXPECTED_DIGEST_HEX:
        print(json.dumps({"error": "digest_mismatch", "got": digest, "expected": EXPECTED_DIGEST_HEX}, ensure_ascii=False))
        return 1

    print(json.dumps({"ok": True, "raw": raw, "digest": digest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

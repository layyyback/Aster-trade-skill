#!/usr/bin/env python3
"""Get current position risk (V3)."""

import argparse
import json
import sys
from decimal import Decimal

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def compact_position(x: dict) -> dict:
    keys = [
        "symbol",
        "positionSide",
        "positionAmt",
        "entryPrice",
        "markPrice",
        "unRealizedProfit",
        "liquidationPrice",
        "leverage",
        "marginType",
    ]
    return {k: x.get(k) for k in keys if k in x}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Get Aster V3 positions")
    p.add_argument("--symbol", help="Optional symbol filter")
    p.add_argument("--non-zero-only", action="store_true")
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)
        params = {"symbol": args.symbol} if args.symbol else {}
        code, body = c.signed_request("GET", "/fapi/v3/positionRisk", params)

        if args.verbose:
            out = format_exchange_response(code, body)
        else:
            items = body if isinstance(body, list) else []
            if args.non_zero_only:
                filtered = []
                for row in items:
                    try:
                        if Decimal(str(row.get("positionAmt", "0"))) != 0:
                            filtered.append(row)
                    except Exception:
                        continue
                items = filtered
            out = {"status_code": code, "body": [compact_position(x) for x in items]}

        print(json.dumps({"positions": out}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

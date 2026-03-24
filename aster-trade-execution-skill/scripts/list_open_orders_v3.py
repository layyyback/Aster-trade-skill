#!/usr/bin/env python3
"""List current open orders (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, compact_order_fields, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="List Aster V3 open orders")
    p.add_argument("--symbol", help="Optional symbol filter")
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
        code, body = c.signed_request("GET", "/fapi/v3/openOrders", params)

        if args.verbose:
            out = format_exchange_response(code, body)
        else:
            entries = body if isinstance(body, list) else []
            out = {"status_code": code, "body": [compact_order_fields(x) for x in entries]}

        print(json.dumps({"open_orders": out}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

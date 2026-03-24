#!/usr/bin/env python3
"""Cancel all open orders for a symbol (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cancel all open orders")
    p.add_argument("--symbol", required=True)
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)
        code, body = c.signed_request("DELETE", "/fapi/v3/allOpenOrders", {"symbol": args.symbol})
        print(json.dumps({"cancel_all": format_exchange_response(code, body)}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

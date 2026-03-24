#!/usr/bin/env python3
"""Modify isolated position margin (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Modify isolated margin")
    p.add_argument("--symbol", required=True)
    p.add_argument("--amount", required=True, help="Margin amount")
    p.add_argument("--type", required=True, choices=["1", "2"], help="1=add,2=reduce")
    p.add_argument("--position-side", choices=["BOTH", "LONG", "SHORT"], default="BOTH")
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
        params = {
            "symbol": args.symbol,
            "amount": args.amount,
            "type": args.type,
            "positionSide": args.position_side,
        }
        code, body = c.signed_request("POST", "/fapi/v3/positionMargin", params)
        print(json.dumps({"modify_isolated_margin": format_exchange_response(code, body)}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

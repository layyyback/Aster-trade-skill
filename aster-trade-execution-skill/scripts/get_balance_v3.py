#!/usr/bin/env python3
"""Get Aster Futures V3 balance."""

import argparse
import json
import sys

from v3_common import (
    AsterV3Client,
    compact_balance_fields,
    format_exchange_response,
    load_env_file,
    require_env,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Get Aster V3 balance")
    parser.add_argument("--asset", help="Optional single asset filter, e.g. USDT")
    parser.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    parser.add_argument("--base-url", default="https://fapi.asterdex.com")
    parser.add_argument("--recv-window", type=int, default=5000)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.env_file:
            load_env_file(args.env_file)

        client = AsterV3Client(
            base_url=args.base_url,
            user=require_env("ASTER_USER"),
            signer=require_env("ASTER_SIGNER"),
            private_key=require_env("ASTER_SIGNER_PRIVATE_KEY"),
            recv_window=args.recv_window,
        )

        code, body = client.signed_request("GET", "/fapi/v3/balance", {})
        if args.verbose:
            out = format_exchange_response(code, body)
        else:
            entries = body if isinstance(body, list) else []
            if args.asset:
                entries = [e for e in entries if str(e.get("asset", "")).upper() == args.asset.upper()]
            out = {
                "status_code": code,
                "body": [compact_balance_fields(e) for e in entries],
            }
        print(json.dumps({"balance": out}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

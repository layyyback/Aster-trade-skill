#!/usr/bin/env python3
"""Set Aster Futures V3 leverage for symbol."""

import argparse
import json
import sys

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Set Aster V3 leverage")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--leverage", required=True, type=int)
    parser.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    parser.add_argument("--base-url", default="https://fapi.asterdex.com")
    parser.add_argument("--recv-window", type=int, default=5000)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.leverage <= 0:
            raise ValueError("--leverage must be > 0")

        if args.env_file:
            load_env_file(args.env_file)

        client = AsterV3Client(
            base_url=args.base_url,
            user=require_env("ASTER_USER"),
            signer=require_env("ASTER_SIGNER"),
            private_key=require_env("ASTER_SIGNER_PRIVATE_KEY"),
            recv_window=args.recv_window,
        )

        code, body = client.signed_request(
            "POST",
            "/fapi/v3/leverage",
            {"symbol": args.symbol, "leverage": str(args.leverage)},
        )
        print(json.dumps({"set_leverage": format_exchange_response(code, body)}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

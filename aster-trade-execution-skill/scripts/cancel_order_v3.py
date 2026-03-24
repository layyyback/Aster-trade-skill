#!/usr/bin/env python3
"""Cancel Aster Futures V3 order by orderId/clientOrderId."""

import argparse
import json
import sys

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cancel Aster V3 order")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--order-id", help="Numeric order id")
    parser.add_argument("--orig-client-order-id", help="Original client order id")
    parser.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    parser.add_argument("--base-url", default="https://fapi.asterdex.com")
    parser.add_argument("--recv-window", type=int, default=5000)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if bool(args.order_id) == bool(args.orig_client_order_id):
            raise ValueError("Provide exactly one of --order-id or --orig-client-order-id")

        if args.env_file:
            load_env_file(args.env_file)

        client = AsterV3Client(
            base_url=args.base_url,
            user=require_env("ASTER_USER"),
            signer=require_env("ASTER_SIGNER"),
            private_key=require_env("ASTER_SIGNER_PRIVATE_KEY"),
            recv_window=args.recv_window,
        )

        params = {"symbol": args.symbol}
        if args.order_id:
            params["orderId"] = args.order_id
        else:
            params["origClientOrderId"] = args.orig_client_order_id

        code, body = client.signed_request("DELETE", "/fapi/v3/order", params)
        print(json.dumps({"cancel_order": format_exchange_response(code, body)}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

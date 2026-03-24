#!/usr/bin/env python3
"""Cancel batch orders by IDs (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def parse_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Cancel batch orders")
    p.add_argument("--symbol", required=True)
    p.add_argument("--order-ids", help="Comma-separated order IDs")
    p.add_argument("--client-order-ids", help="Comma-separated original client order IDs")
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if bool(args.order_ids) == bool(args.client_order_ids):
            raise ValueError("Provide exactly one of --order-ids or --client-order-ids")

        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)
        params = {"symbol": args.symbol}
        if args.order_ids:
            params["orderIdList"] = json.dumps([int(x) for x in parse_csv(args.order_ids)], separators=(",", ":"))
        else:
            params["origClientOrderIdList"] = json.dumps(parse_csv(args.client_order_ids), separators=(",", ":"))

        code, body = c.signed_request("DELETE", "/fapi/v3/batchOrders", params)
        print(json.dumps({"cancel_batch": format_exchange_response(code, body)}, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

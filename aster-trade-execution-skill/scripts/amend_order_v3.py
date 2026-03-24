#!/usr/bin/env python3
"""Amend order by cancel + replace (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, compact_order_fields, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Amend order via cancel+replace")
    p.add_argument("--symbol", required=True)
    p.add_argument("--order-id", help="Existing orderId")
    p.add_argument("--orig-client-order-id", help="Existing clientOrderId")
    p.add_argument("--new-price", required=True)
    p.add_argument("--new-quantity", required=True)
    p.add_argument("--time-in-force", default="GTC")
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if bool(args.order_id) == bool(args.orig_client_order_id):
            raise ValueError("Provide exactly one of --order-id or --orig-client-order-id")

        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)

        q_params = {"symbol": args.symbol}
        if args.order_id:
            q_params["orderId"] = args.order_id
        else:
            q_params["origClientOrderId"] = args.orig_client_order_id

        q_code, q_body = c.signed_request("GET", "/fapi/v3/order", q_params)
        out = {"query_old_order": format_exchange_response(q_code, q_body)}
        if q_code != 200 or not isinstance(q_body, dict):
            print(json.dumps(out, ensure_ascii=False))
            return 1

        cancel_code, cancel_body = c.signed_request("DELETE", "/fapi/v3/order", q_params)
        out["cancel_old_order"] = format_exchange_response(cancel_code, cancel_body)
        if cancel_code != 200:
            print(json.dumps(out, ensure_ascii=False))
            return 1

        new_params = {
            "symbol": args.symbol,
            "side": q_body.get("side"),
            "positionSide": q_body.get("positionSide", "BOTH"),
            "type": "LIMIT",
            "timeInForce": args.time_in_force,
            "price": args.new_price,
            "quantity": args.new_quantity,
            "reduceOnly": "true" if q_body.get("reduceOnly") else None,
        }
        n_code, n_body = c.signed_request("POST", "/fapi/v3/order", new_params)
        out["new_order"] = format_exchange_response(n_code, n_body)

        if n_code == 200 and isinstance(n_body, dict) and n_body.get("orderId"):
            check_code, check_body = c.signed_request("GET", "/fapi/v3/order", {"symbol": args.symbol, "orderId": str(n_body["orderId"])})
            if args.verbose:
                out["query_new_order"] = format_exchange_response(check_code, check_body)
            else:
                out["query_new_order"] = {"status_code": check_code, "body": compact_order_fields(check_body) if isinstance(check_body, dict) else check_body}

        print(json.dumps(out, ensure_ascii=False))
        return 0 if n_code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

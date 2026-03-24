#!/usr/bin/env python3
"""Place conditional STOP/TAKE_PROFIT order (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, compact_order_fields, format_exchange_response, load_env_file, require_env


TYPES = {"STOP", "STOP_MARKET", "TAKE_PROFIT", "TAKE_PROFIT_MARKET", "TRAILING_STOP_MARKET"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Place Aster conditional order")
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY", "SELL"])
    p.add_argument("--type", required=True, choices=sorted(TYPES))
    p.add_argument("--position-side", default="BOTH", choices=["BOTH", "LONG", "SHORT"])
    p.add_argument("--stop-price", help="Required for STOP/STOP_MARKET/TAKE_PROFIT/TAKE_PROFIT_MARKET")
    p.add_argument("--price", help="Required for STOP/TAKE_PROFIT")
    p.add_argument("--quantity", help="Required unless --close-position true for *_MARKET")
    p.add_argument("--close-position", action="store_true")
    p.add_argument("--reduce-only", action="store_true")
    p.add_argument("--activation-price", help="Used with TRAILING_STOP_MARKET")
    p.add_argument("--callback-rate", help="Used with TRAILING_STOP_MARKET, min 0.1 max 5 (1 = 1%%)")
    p.add_argument("--time-in-force", default="GTC")
    p.add_argument("--working-type", default="CONTRACT_PRICE", choices=["MARK_PRICE", "CONTRACT_PRICE"])
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

        t = args.type.upper()
        if t == "TRAILING_STOP_MARKET":
            if not args.callback_rate:
                raise ValueError("--callback-rate is required for TRAILING_STOP_MARKET")
            if args.stop_price:
                raise ValueError("--stop-price is not used by TRAILING_STOP_MARKET")
            if args.price:
                raise ValueError("--price is not used by TRAILING_STOP_MARKET")
        else:
            if not args.stop_price:
                raise ValueError("--stop-price is required for this order type")
            if t in {"STOP", "TAKE_PROFIT"} and not args.price:
                raise ValueError("--price is required for STOP/TAKE_PROFIT")
            if t in {"STOP_MARKET", "TAKE_PROFIT_MARKET"} and args.price:
                raise ValueError("--price is not used by *_MARKET types")
        if args.close_position and args.quantity:
            raise ValueError("--close-position and --quantity are mutually exclusive")
        if t != "TRAILING_STOP_MARKET" and not args.close_position and not args.quantity:
            raise ValueError("--quantity is required when --close-position is false")

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)

        params = {
            "symbol": args.symbol,
            "side": args.side,
            "type": t,
            "positionSide": args.position_side,
            "stopPrice": args.stop_price if t != "TRAILING_STOP_MARKET" else None,
            "workingType": args.working_type,
            "reduceOnly": "true" if args.reduce_only else None,
            "closePosition": "true" if args.close_position else None,
            "quantity": args.quantity,
            "price": args.price,
            "timeInForce": args.time_in_force if t in {"STOP", "TAKE_PROFIT"} else None,
            "activationPrice": args.activation_price if t == "TRAILING_STOP_MARKET" else None,
            "callbackRate": args.callback_rate if t == "TRAILING_STOP_MARKET" else None,
        }

        code, body = c.signed_request("POST", "/fapi/v3/order", params)
        out = {"place_conditional": format_exchange_response(code, body)}

        if code == 200 and isinstance(body, dict) and body.get("orderId"):
            q_code, q_body = c.signed_request("GET", "/fapi/v3/order", {"symbol": args.symbol, "orderId": str(body["orderId"])})
            if args.verbose:
                out["query_order"] = format_exchange_response(q_code, q_body)
            else:
                out["query_order"] = {"status_code": q_code, "body": compact_order_fields(q_body) if isinstance(q_body, dict) else q_body}

        print(json.dumps(out, ensure_ascii=False))
        return 0 if code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

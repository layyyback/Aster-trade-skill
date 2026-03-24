#!/usr/bin/env python3
"""Close position via market reduce-only order (V3)."""

import argparse
import json
import sys
from decimal import Decimal

from v3_common import AsterV3Client, compact_order_fields, format_exchange_response, load_env_file, require_env


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Close position with market reduce-only order")
    p.add_argument("--symbol", required=True)
    p.add_argument("--position-side", default="BOTH", choices=["BOTH", "LONG", "SHORT"])
    p.add_argument("--quantity", help="Optional close quantity; default closes full side")
    p.add_argument("--side", choices=["BUY", "SELL"], help="Optional close side override (recommended only for hedge mode)")
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def get_position_amt(rows: list[dict], symbol: str, position_side: str) -> Decimal:
    for row in rows:
        if row.get("symbol") != symbol:
            continue
        if str(row.get("positionSide", "")).upper() != position_side:
            continue
        return Decimal(str(row.get("positionAmt", "0")))
    return Decimal("0")


def main() -> int:
    try:
        args = parse_args()
        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)

        position_side = args.position_side.upper()
        p_code, p_body = c.signed_request("GET", "/fapi/v3/positionRisk", {"symbol": args.symbol})
        if p_code != 200 or not isinstance(p_body, list):
            out = {"positions": format_exchange_response(p_code, p_body)}
            print(json.dumps(out, ensure_ascii=False))
            return 1

        pos_amt = get_position_amt(p_body, args.symbol, position_side)
        if pos_amt == 0:
            raise ValueError("No open position found for requested symbol/position-side")

        full_qty = abs(pos_amt)
        if args.quantity:
            qty = Decimal(args.quantity)
            if qty <= 0:
                raise ValueError("--quantity must be > 0")
            if qty > full_qty:
                raise ValueError(f"Requested quantity exceeds open position: {qty} > {full_qty}")
        else:
            qty = full_qty

        if args.side:
            side = args.side
        else:
            if position_side == "BOTH":
                side = "SELL" if pos_amt > 0 else "BUY"
            else:
                side = "SELL" if position_side == "LONG" else "BUY"

        params = {
            "symbol": args.symbol,
            "positionSide": position_side,
            "type": "MARKET",
            "side": side,
            "quantity": str(qty),
            "reduceOnly": "true",
        }
        code, body = c.signed_request("POST", "/fapi/v3/order", params)
        out = {
            "close_request": {
                "symbol": args.symbol,
                "positionSide": position_side,
                "side": side,
                "quantity": str(qty),
            },
            "close_order": format_exchange_response(code, body),
        }

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

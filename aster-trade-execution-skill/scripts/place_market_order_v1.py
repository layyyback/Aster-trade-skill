#!/usr/bin/env python3
"""Place Aster Futures V1 market order (dry-run by default)."""

import argparse
import json
import sys
from decimal import Decimal, ROUND_DOWN, InvalidOperation

from v1_common import AsterV1Client, format_exchange_response, load_env_file, require_env


def floor_to_step(v: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return v
    return (v / step).to_integral_value(rounding=ROUND_DOWN) * step


def ceil_to_step(v: Decimal, step: Decimal) -> Decimal:
    f = floor_to_step(v, step)
    if f == v:
        return v
    return f + step


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Place Aster V1 market order")
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY", "SELL"])
    p.add_argument("--position-side", default="BOTH", choices=["BOTH", "LONG", "SHORT"])
    p.add_argument("--notional-usdt")
    p.add_argument("--quantity")
    p.add_argument("--notional-rounding", default="floor", choices=["floor", "ceil", "nearest"])
    p.add_argument("--leverage", type=int)
    p.add_argument("--reduce-only", action="store_true")
    p.add_argument("--skip-prefetch", action="store_true")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--env-file")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if bool(args.quantity) == bool(args.notional_usdt):
            raise ValueError("Provide exactly one of --quantity or --notional-usdt")
        if args.skip_prefetch and not args.quantity:
            raise ValueError("--skip-prefetch requires explicit --quantity")
        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV1Client(args.base_url, require_env("ASTER_API_KEY"), require_env("ASTER_SECRET_KEY"), args.recv_window)
        out = {"version": "v1", "dry_run": not args.execute, "symbol": args.symbol, "side": args.side}

        b_code, b_body = c.signed_request("GET", "/fapi/v1/balance", {})
        out["auth_balance_check"] = format_exchange_response(b_code, b_body)
        if b_code != 200:
            print(json.dumps(out, ensure_ascii=False))
            return 1

        ref_price = None
        min_qty = step = max_qty = min_notional = None
        if not args.skip_prefetch:
            ref_price = Decimal(str(c.public_get("/fapi/v1/ticker/price", {"symbol": args.symbol})["price"]))
            ex = c.public_get("/fapi/v1/exchangeInfo", {"symbol": args.symbol})
            sym = next((s for s in ex.get("symbols", []) if s.get("symbol") == args.symbol), None)
            if not sym:
                raise ValueError("symbol not found")
            fs = {f["filterType"]: f for f in sym.get("filters", [])}
            lot = fs.get("MARKET_LOT_SIZE") or fs.get("LOT_SIZE")
            min_qty = Decimal(str(lot.get("minQty", "0")))
            max_qty = Decimal(str(lot.get("maxQty", "999999999")))
            step = Decimal(str(lot.get("stepSize", "0.001")))
            min_notional = Decimal(str(fs.get("MIN_NOTIONAL", {}).get("notional", "0")))

        target_notional = None
        if args.quantity:
            qty = Decimal(args.quantity)
        else:
            target_notional = Decimal(args.notional_usdt)
            raw = target_notional / ref_price
            qf = floor_to_step(raw, step)
            qc = ceil_to_step(raw, step)
            if qf < min_qty:
                qf = min_qty
            if qc < min_qty:
                qc = min_qty
            if args.notional_rounding == "floor":
                qty = qf
            elif args.notional_rounding == "ceil":
                qty = qc
            else:
                qty = qf if abs(qf * ref_price - target_notional) <= abs(qc * ref_price - target_notional) else qc

        if qty <= 0:
            raise ValueError("quantity must be > 0")
        if min_qty is not None and qty < min_qty:
            raise ValueError("quantity < minQty")
        if step is not None and floor_to_step(qty, step) != qty:
            raise ValueError("quantity not aligned to stepSize")
        if max_qty is not None and qty > max_qty:
            raise ValueError("quantity > maxQty")
        if min_notional is not None and ref_price is not None and (qty * ref_price) < min_notional:
            raise ValueError("notional < minNotional")

        params = {
            "symbol": args.symbol,
            "positionSide": args.position_side,
            "type": "MARKET",
            "side": args.side,
            "quantity": str(qty),
            "reduceOnly": "true" if args.reduce_only else None,
        }
        out["plan"] = {"order_params": params}
        if ref_price is not None:
            actual = qty * ref_price
            out["plan"]["ref_price"] = str(ref_price)
            out["plan"]["actual_notional"] = str(actual.normalize())
            if target_notional is not None:
                out["plan"]["target_notional"] = str(target_notional.normalize())
                out["plan"]["notional_delta"] = str((actual - target_notional).normalize())
                out["plan"]["notional_rounding"] = args.notional_rounding
        if args.skip_prefetch:
            out["plan"]["warnings"] = ["skip_prefetch enabled: filters not pre-validated"]

        if not args.execute:
            print(json.dumps(out, ensure_ascii=False))
            return 0

        if args.leverage is not None:
            l_code, l_body = c.signed_request("POST", "/fapi/v1/leverage", {"symbol": args.symbol, "leverage": str(args.leverage)})
            out["set_leverage"] = format_exchange_response(l_code, l_body)
            if l_code != 200:
                print(json.dumps(out, ensure_ascii=False))
                return 1

        p_code, p_body = c.signed_request("POST", "/fapi/v1/order", params)
        out["place_order"] = format_exchange_response(p_code, p_body)
        if p_code == 200 and isinstance(p_body, dict) and p_body.get("orderId"):
            q_code, q_body = c.signed_request("GET", "/fapi/v1/order", {"symbol": args.symbol, "orderId": str(p_body["orderId"])})
            out["query_order"] = format_exchange_response(q_code, q_body)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if p_code == 200 else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

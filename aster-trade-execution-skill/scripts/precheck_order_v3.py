#!/usr/bin/env python3
"""Precheck order feasibility before submission (V3)."""

import argparse
import json
import sys
from decimal import Decimal, ROUND_DOWN, InvalidOperation

from v3_common import AsterV3Client, load_env_file, require_env


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Precheck Aster order")
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY", "SELL"])
    p.add_argument("--notional-usdt", help="Target notional")
    p.add_argument("--quantity", help="Base quantity")
    p.add_argument("--leverage", type=int, default=1)
    p.add_argument("--asset", default="USDT")
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if bool(args.notional_usdt) == bool(args.quantity):
            raise ValueError("Provide exactly one of --notional-usdt or --quantity")

        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)

        ticker = c.public_get("/fapi/v3/ticker/price", {"symbol": args.symbol})
        price = Decimal(str(ticker["price"]))

        ex = c.public_get("/fapi/v3/exchangeInfo", {"symbol": args.symbol})
        sym = next((s for s in ex.get("symbols", []) if s.get("symbol") == args.symbol), None)
        if not sym:
            raise ValueError("symbol not found")

        filters = {f["filterType"]: f for f in sym.get("filters", [])}
        lot = filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE")
        min_qty = Decimal(str(lot.get("minQty", "0")))
        max_qty = Decimal(str(lot.get("maxQty", "999999999")))
        step_size = Decimal(str(lot.get("stepSize", "0.001")))
        min_notional = Decimal(str(filters.get("MIN_NOTIONAL", {}).get("notional", "5")))

        if args.quantity:
            qty = Decimal(args.quantity)
        else:
            try:
                target = Decimal(args.notional_usdt)
            except InvalidOperation as exc:
                raise ValueError("invalid notional") from exc
            qty = floor_to_step(target / price, step_size)
            if qty < min_qty:
                qty = min_qty

        notional = qty * price

        b_code, b_body = c.signed_request("GET", "/fapi/v3/balance", {})
        available = Decimal("0")
        if b_code == 200 and isinstance(b_body, list):
            row = next((x for x in b_body if str(x.get("asset", "")).upper() == args.asset.upper()), None)
            if row:
                available = Decimal(str(row.get("availableBalance", "0")))

        required_margin = notional / Decimal(max(args.leverage, 1))
        checks = {
            "qty_ge_min": qty >= min_qty,
            "qty_le_max": qty <= max_qty,
            "notional_ge_min": notional >= min_notional,
            "margin_sufficient_estimate": available >= required_margin,
        }

        out = {
            "symbol": args.symbol,
            "side": args.side,
            "ref_price": str(price),
            "quantity": str(qty),
            "notional": str(notional.normalize()),
            "estimated_required_margin": str(required_margin.normalize()),
            "available_balance": str(available),
            "filters": {
                "min_qty": str(min_qty),
                "max_qty": str(max_qty),
                "step_size": str(step_size),
                "min_notional": str(min_notional),
            },
            "checks": checks,
            "ok": all(checks.values()),
            "suggested_order_params": {
                "symbol": args.symbol,
                "side": args.side,
                "type": "MARKET",
                "quantity": str(qty),
            },
        }

        print(json.dumps(out, ensure_ascii=False))
        return 0 if out["ok"] else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

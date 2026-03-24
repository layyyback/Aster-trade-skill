#!/usr/bin/env python3
"""Unified V3 market order script with safety-first dry-run mode."""

import argparse
import json
import sys
from decimal import Decimal, ROUND_DOWN, InvalidOperation

from v3_common import (
    AsterV3Client,
    compact_order_fields,
    format_exchange_response,
    load_env_file,
    require_env,
)


def floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def ceil_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    floored = floor_to_step(value, step)
    if floored == value:
        return value
    return floored + step


def choose_market_filters(symbol_info: dict) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    filters = {f["filterType"]: f for f in symbol_info.get("filters", [])}
    lot = filters.get("MARKET_LOT_SIZE") or filters.get("LOT_SIZE")
    if not lot:
        raise ValueError("Symbol filters missing MARKET_LOT_SIZE/LOT_SIZE")
    min_qty = Decimal(lot["minQty"])
    step_size = Decimal(lot["stepSize"])
    max_qty = Decimal(lot.get("maxQty", "999999999"))
    min_notional = Decimal(filters.get("MIN_NOTIONAL", {}).get("notional", "0"))
    return min_qty, step_size, max_qty, min_notional


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Place Aster V3 market order (dry-run by default)")
    p.add_argument("--symbol", required=True)
    p.add_argument("--side", required=True, choices=["BUY", "SELL"])
    p.add_argument("--position-side", default="BOTH", choices=["BOTH", "LONG", "SHORT"])
    p.add_argument("--notional-usdt", help="Target USDT notional")
    p.add_argument("--notional-rounding", default="floor", choices=["floor", "ceil", "nearest"], help="Rounding strategy when converting notional to quantity")
    p.add_argument("--quantity", help="Base quantity")
    p.add_argument("--leverage", type=int, help="Optional leverage setting before order")
    p.add_argument("--reduce-only", action="store_true")
    p.add_argument("--skip-prefetch", action="store_true", help="Advanced mode: skip ticker/exchangeInfo prechecks (requires --quantity)")
    p.add_argument("--execute", action="store_true", help="Actually send order. Default is dry-run only.")
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    p.add_argument("--verbose", action="store_true")
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

        client = AsterV3Client(
            base_url=args.base_url,
            user=require_env("ASTER_USER"),
            signer=require_env("ASTER_SIGNER"),
            private_key=require_env("ASTER_SIGNER_PRIVATE_KEY"),
            recv_window=args.recv_window,
        )

        out = {
            "dry_run": not args.execute,
            "symbol": args.symbol,
            "side": args.side,
            "positionSide": args.position_side,
            "skip_prefetch": bool(args.skip_prefetch),
        }

        # Step 1: auth + balance check
        b_code, b_body = client.signed_request("GET", "/fapi/v3/balance", {})
        out["auth_balance_check"] = format_exchange_response(b_code, b_body)
        if b_code != 200:
            print(json.dumps(out, ensure_ascii=False))
            return 1

        qty: Decimal
        ref_price = None
        min_qty = None
        step_size = None
        max_qty = None
        min_notional = None

        # Step 2: exchange filters prefetch
        if not args.skip_prefetch:
            ticker = client.public_get("/fapi/v3/ticker/price", {"symbol": args.symbol})
            ref_price = Decimal(str(ticker["price"]))
            ex = client.public_get("/fapi/v3/exchangeInfo", {"symbol": args.symbol})
            sym = next((s for s in ex.get("symbols", []) if s.get("symbol") == args.symbol), None)
            if not sym:
                raise ValueError(f"Symbol not found in exchangeInfo: {args.symbol}")
            min_qty, step_size, max_qty, min_notional = choose_market_filters(sym)

        # Step 3: notional -> quantity
        target_notional = None
        if args.quantity:
            qty = Decimal(args.quantity)
        else:
            try:
                notional = Decimal(args.notional_usdt)
            except InvalidOperation as exc:
                raise ValueError("Invalid --notional-usdt") from exc
            if notional <= 0:
                raise ValueError("--notional-usdt must be > 0")
            target_notional = notional
            raw_qty = notional / ref_price
            qty_floor = floor_to_step(raw_qty, step_size)
            qty_ceil = ceil_to_step(raw_qty, step_size)
            if qty_floor < min_qty:
                qty_floor = min_qty
            if qty_ceil < min_qty:
                qty_ceil = min_qty
            if args.notional_rounding == "floor":
                qty = qty_floor
            elif args.notional_rounding == "ceil":
                qty = qty_ceil
            else:
                floor_diff = abs((qty_floor * ref_price) - notional)
                ceil_diff = abs((qty_ceil * ref_price) - notional)
                qty = qty_floor if floor_diff <= ceil_diff else qty_ceil

        if qty <= 0:
            raise ValueError("Computed quantity must be > 0")
        if min_qty is not None and qty < min_qty:
            raise ValueError(f"Quantity below minQty: {qty} < {min_qty}")
        if step_size is not None and floor_to_step(qty, step_size) != qty:
            raise ValueError(f"Quantity not aligned to stepSize: {qty} (step {step_size})")
        if max_qty is not None and qty > max_qty:
            raise ValueError(f"Quantity exceeds maxQty: {qty} > {max_qty}")
        if min_notional is not None and min_notional > 0 and ref_price is not None:
            est_notional = qty * ref_price
            if est_notional < min_notional:
                raise ValueError(f"Estimated notional below MIN_NOTIONAL: {est_notional} < {min_notional}")

        if args.position_side in ("LONG", "SHORT") and args.reduce_only:
            raise ValueError("Invalid combination: reduceOnly with hedge-side open order")

        order_params = {
            "symbol": args.symbol,
            "positionSide": args.position_side,
            "type": "MARKET",
            "side": args.side,
            "quantity": str(qty),
            "reduceOnly": "true" if args.reduce_only else None,
        }

        out["plan"] = {
            "leverage": args.leverage,
            "order_params": order_params,
            "ref_price": str(ref_price) if ref_price is not None else None,
            "min_qty": str(min_qty) if min_qty is not None else None,
            "step_size": str(step_size) if step_size is not None else None,
            "max_qty": str(max_qty) if max_qty is not None else None,
            "min_notional": str(min_notional) if min_notional is not None else None,
            "warnings": [
                "skip_prefetch enabled: exchange filters and MIN_NOTIONAL were not pre-validated"
            ] if args.skip_prefetch else [],
        }
        if ref_price is not None:
            actual_notional = qty * ref_price
            out["plan"]["actual_notional"] = str(actual_notional.normalize())
            if target_notional is not None:
                out["plan"]["target_notional"] = str(target_notional.normalize())
                out["plan"]["notional_delta"] = str((actual_notional - target_notional).normalize())
                out["plan"]["notional_rounding"] = args.notional_rounding

        if not args.execute:
            print(json.dumps(out, ensure_ascii=False))
            return 0

        # Step 4: leverage setup
        if args.leverage is not None:
            l_code, l_body = client.signed_request("POST", "/fapi/v3/leverage", {"symbol": args.symbol, "leverage": str(args.leverage)})
            out["set_leverage"] = format_exchange_response(l_code, l_body)
            if l_code != 200:
                print(json.dumps(out, ensure_ascii=False))
                return 1

        # Step 5: place order
        p_code, p_body = client.signed_request("POST", "/fapi/v3/order", order_params)
        out["place_order"] = format_exchange_response(p_code, p_body)
        if p_code != 200:
            print(json.dumps(out, ensure_ascii=False))
            return 1

        order_id = str(p_body.get("orderId", "")) if isinstance(p_body, dict) else ""
        if order_id:
            q_code, q_body = client.signed_request("GET", "/fapi/v3/order", {"symbol": args.symbol, "orderId": order_id})
            if args.verbose:
                out["query_order"] = format_exchange_response(q_code, q_body)
            else:
                out["query_order"] = {
                    "status_code": q_code,
                    "body": compact_order_fields(q_body) if isinstance(q_body, dict) else q_body,
                }

        print(json.dumps(out, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

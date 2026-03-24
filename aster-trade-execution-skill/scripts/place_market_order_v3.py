#!/usr/bin/env python3
"""Place Aster Futures V3 market order."""

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
    parser = argparse.ArgumentParser(description="Place Aster V3 market order")
    parser.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"])
    parser.add_argument("--position-side", default="BOTH", choices=["BOTH", "LONG", "SHORT"])
    parser.add_argument("--quantity", help="Base quantity, e.g. 0.001")
    parser.add_argument("--notional-usdt", help="Target notional in USDT, e.g. 100")
    parser.add_argument("--notional-rounding", default="floor", choices=["floor", "ceil", "nearest"], help="Rounding strategy when converting notional to quantity")
    parser.add_argument("--leverage", type=int, help="Set leverage before placing order")
    parser.add_argument("--reduce-only", action="store_true")
    parser.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    parser.add_argument("--base-url", default="https://fapi.asterdex.com")
    parser.add_argument("--recv-window", type=int, default=5000)
    parser.add_argument("--skip-prefetch", action="store_true", help="Advanced mode: skip ticker/exchangeInfo fetch")
    parser.add_argument("--verbose", action="store_true", help="Return full exchange payloads")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()

        if bool(args.quantity) == bool(args.notional_usdt):
            raise ValueError("Provide exactly one of --quantity or --notional-usdt")

        if args.env_file:
            load_env_file(args.env_file)

        user = require_env("ASTER_USER")
        signer = require_env("ASTER_SIGNER")
        private_key = require_env("ASTER_SIGNER_PRIVATE_KEY")

        client = AsterV3Client(
            base_url=args.base_url,
            user=user,
            signer=signer,
            private_key=private_key,
            recv_window=args.recv_window,
        )

        result: dict = {"symbol": args.symbol, "side": args.side}

        # Auth + balance precheck
        b_code, b_body = client.signed_request("GET", "/fapi/v3/balance", {})
        result["auth_balance_check"] = format_exchange_response(b_code, b_body)
        if b_code != 200:
            print(json.dumps(result, ensure_ascii=False))
            return 1

        if args.leverage is not None:
            code, body = client.signed_request(
                "POST",
                "/fapi/v3/leverage",
                {"symbol": args.symbol, "leverage": str(args.leverage)},
            )
            result["set_leverage"] = format_exchange_response(code, body)
            if code != 200:
                print(json.dumps(result, ensure_ascii=False))
                return 1

        qty: Decimal
        ref_price = None
        min_qty = None
        step_size = None
        max_qty = None
        min_notional = None

        if args.skip_prefetch and not args.quantity:
            raise ValueError("--skip-prefetch requires explicit --quantity")

        if not args.skip_prefetch:
            ticker = client.public_get("/fapi/v3/ticker/price", {"symbol": args.symbol})
            ref_price = Decimal(str(ticker["price"]))

            exchange_info = client.public_get("/fapi/v3/exchangeInfo", {"symbol": args.symbol})
            symbols = exchange_info.get("symbols", [])
            symbol_info = next((s for s in symbols if s.get("symbol") == args.symbol), None)
            if not symbol_info:
                raise ValueError(f"Symbol not found in exchangeInfo: {args.symbol}")

            min_qty, step_size, max_qty, min_notional = choose_market_filters(symbol_info)

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
            raise ValueError(f"Quantity does not align with stepSize: {qty} (step {step_size})")
        if max_qty is not None and qty > max_qty:
            raise ValueError(f"Computed quantity exceeds maxQty: {qty} > {max_qty}")
        if args.position_side in ("LONG", "SHORT") and args.reduce_only:
            raise ValueError("Invalid combination: reduce-only with hedge-side open order request")
        if min_notional is not None and min_notional > 0 and ref_price is not None:
            est_notional = qty * ref_price
            if est_notional < min_notional:
                raise ValueError(
                    f"Estimated notional below MIN_NOTIONAL: {est_notional} < {min_notional}"
                )

        order_params = {
            "symbol": args.symbol,
            "positionSide": args.position_side,
            "type": "MARKET",
            "side": args.side,
            "quantity": str(qty),
            "reduceOnly": "true" if args.reduce_only else None,
        }

        result["request"] = {
            "type": "MARKET",
            "quantity": str(qty),
            "positionSide": args.position_side,
            "reduceOnly": bool(args.reduce_only),
            "skip_prefetch": bool(args.skip_prefetch),
        }
        if args.skip_prefetch:
            result["warnings"] = [
                "skip_prefetch enabled: exchange filters and MIN_NOTIONAL were not pre-validated"
            ]
        if ref_price is not None:
            result["request"]["ref_price"] = str(ref_price)
            actual_notional = qty * ref_price
            result["request"]["est_notional"] = str(actual_notional.normalize())
            if target_notional is not None:
                result["request"]["target_notional"] = str(target_notional.normalize())
                result["request"]["notional_delta"] = str((actual_notional - target_notional).normalize())
                result["request"]["notional_rounding"] = args.notional_rounding
        if min_qty is not None:
            result["request"]["min_qty"] = str(min_qty)
        if step_size is not None:
            result["request"]["step_size"] = str(step_size)
        if max_qty is not None:
            result["request"]["max_qty"] = str(max_qty)
        if min_notional is not None:
            result["request"]["min_notional"] = str(min_notional)

        code, body = client.signed_request("POST", "/fapi/v3/order", order_params)
        result["place_order"] = format_exchange_response(code, body)
        if code != 200:
            print(json.dumps(result, ensure_ascii=False))
            return 1

        order_id = str(body.get("orderId", ""))
        if order_id:
            q_code, q_body = client.signed_request(
                "GET",
                "/fapi/v3/order",
                {"symbol": args.symbol, "orderId": order_id},
            )
            if args.verbose:
                result["query_order"] = format_exchange_response(q_code, q_body)
            else:
                compact = compact_order_fields(q_body) if isinstance(q_body, dict) else q_body
                result["query_order"] = {"status_code": q_code, "body": compact}

        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

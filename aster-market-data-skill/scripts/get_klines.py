#!/usr/bin/env python3
"""Get kline/candlestick data."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json

INTERVALS = [
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
]


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get kline data")
        p.add_argument("--symbol", required=True)
        p.add_argument("--interval", required=True, choices=INTERVALS)
        p.add_argument("--start-time", type=int, help="Start time in ms")
        p.add_argument("--end-time", type=int, help="End time in ms")
        p.add_argument("--limit", type=int, default=500, help="Max 1500")
        add_base_url_arg(p)
        args = p.parse_args()

        params = {"symbol": args.symbol, "interval": args.interval, "limit": args.limit}
        if args.start_time:
            params["startTime"] = args.start_time
        if args.end_time:
            params["endTime"] = args.end_time

        c = AsterMarketClient(args.base_url)
        return output_json(c.get("/fapi/v3/klines", params))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

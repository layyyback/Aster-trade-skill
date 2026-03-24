#!/usr/bin/env python3
"""Get funding rate history."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get funding rate history")
        p.add_argument("--symbol", help="e.g. BTCUSDT")
        p.add_argument("--start-time", type=int, help="Start time in ms")
        p.add_argument("--end-time", type=int, help="End time in ms")
        p.add_argument("--limit", type=int, default=100, help="Max 1000")
        add_base_url_arg(p)
        args = p.parse_args()

        params = {"limit": args.limit}
        if args.symbol:
            params["symbol"] = args.symbol
        if args.start_time:
            params["startTime"] = args.start_time
        if args.end_time:
            params["endTime"] = args.end_time

        c = AsterMarketClient(args.base_url)
        return output_json(c.get("/fapi/v3/fundingRate", params))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

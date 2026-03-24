#!/usr/bin/env python3
"""Get compressed/aggregate trades."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get aggregate trades")
        p.add_argument("--symbol", required=True)
        p.add_argument("--from-id", type=int, help="Trade ID to fetch from (inclusive)")
        p.add_argument("--start-time", type=int, help="Start time in ms")
        p.add_argument("--end-time", type=int, help="End time in ms")
        p.add_argument("--limit", type=int, default=500, help="Max 1000")
        add_base_url_arg(p)
        args = p.parse_args()

        params = {"symbol": args.symbol, "limit": args.limit}
        if args.from_id is not None:
            params["fromId"] = args.from_id
        if args.start_time:
            params["startTime"] = args.start_time
        if args.end_time:
            params["endTime"] = args.end_time

        c = AsterMarketClient(args.base_url)
        return output_json(c.get("/fapi/v3/aggTrades", params))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

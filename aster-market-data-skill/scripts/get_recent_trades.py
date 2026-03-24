#!/usr/bin/env python3
"""Get recent market trades."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get recent trades")
        p.add_argument("--symbol", required=True)
        p.add_argument("--limit", type=int, default=500, help="Max 1000")
        add_base_url_arg(p)
        args = p.parse_args()

        c = AsterMarketClient(args.base_url)
        return output_json(c.get("/fapi/v3/trades", {"symbol": args.symbol, "limit": args.limit}))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

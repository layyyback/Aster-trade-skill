#!/usr/bin/env python3
"""Get order book depth."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get order book depth")
        p.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
        p.add_argument("--limit", type=int, default=500, choices=[5, 10, 20, 50, 100, 500, 1000])
        add_base_url_arg(p)
        args = p.parse_args()

        c = AsterMarketClient(args.base_url)
        return output_json(c.get("/fapi/v3/depth", {"symbol": args.symbol, "limit": args.limit}))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

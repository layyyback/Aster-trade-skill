#!/usr/bin/env python3
"""Get best bid/ask price and quantity."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get best bid/ask (book ticker)")
        p.add_argument("--symbol", help="e.g. BTCUSDT; omit for all symbols")
        add_base_url_arg(p)
        args = p.parse_args()

        c = AsterMarketClient(args.base_url)
        params = {}
        if args.symbol:
            params["symbol"] = args.symbol
        return output_json(c.get("/fapi/v3/ticker/bookTicker", params))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

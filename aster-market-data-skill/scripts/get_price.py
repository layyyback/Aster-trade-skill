#!/usr/bin/env python3
"""Get latest price for a symbol or all symbols."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get latest price")
        p.add_argument("--symbol", help="e.g. BTCUSDT; omit for all symbols")
        add_base_url_arg(p)
        args = p.parse_args()

        c = AsterMarketClient(args.base_url)
        params = {}
        if args.symbol:
            params["symbol"] = args.symbol
        return output_json(c.get("/fapi/v3/ticker/price", params))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

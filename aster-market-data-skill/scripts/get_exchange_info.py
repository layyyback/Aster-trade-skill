#!/usr/bin/env python3
"""Get exchange trading rules and symbol information."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Get exchange info")
        p.add_argument("--symbol", help="Filter to a specific symbol")
        add_base_url_arg(p)
        args = p.parse_args()

        c = AsterMarketClient(args.base_url)
        data = c.get("/fapi/v3/exchangeInfo")
        if args.symbol:
            symbols = [s for s in data.get("symbols", []) if s.get("symbol") == args.symbol]
            data["symbols"] = symbols
        return output_json(data)
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

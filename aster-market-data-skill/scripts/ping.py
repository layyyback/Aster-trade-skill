#!/usr/bin/env python3
"""Test connectivity to Aster API."""

import argparse
import sys

from market_common import AsterMarketClient, add_base_url_arg, output_error, output_json


def main() -> int:
    try:
        p = argparse.ArgumentParser(description="Ping Aster API")
        add_base_url_arg(p)
        args = p.parse_args()

        c = AsterMarketClient(args.base_url)
        return output_json(c.get("/fapi/v3/ping"))
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

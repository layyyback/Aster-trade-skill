#!/usr/bin/env python3
"""Set margin type (CROSSED/ISOLATED) for symbol (V3)."""

import argparse
import json
import sys

from v3_common import AsterV3Client, format_exchange_response, load_env_file, require_env


def match_noop_margin_type_rule(code: int, body: object) -> tuple[bool, str, str]:
    if code == 200 or not isinstance(body, dict):
        return False, "", ""

    msg_raw = str(body.get("msg", ""))
    msg = msg_raw.lower()
    try:
        error_code = int(body.get("code"))
    except Exception:
        error_code = None

    if error_code == -4046:
        return True, "code_-4046", msg_raw
    if "no need to change" in msg:
        return True, "msg_no_need_to_change", msg_raw
    if "same margin type" in msg:
        return True, "msg_same_margin_type", msg_raw
    if "not modified" in msg:
        return True, "msg_not_modified", msg_raw
    return False, "", ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Set Aster V3 margin type")
    p.add_argument("--symbol", required=True)
    p.add_argument("--margin-type", required=True, choices=["CROSSED", "ISOLATED"])
    p.add_argument("--env-file", help="Optional env file containing ASTER_* vars")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    p.add_argument("--recv-window", type=int, default=5000)
    return p.parse_args()


def main() -> int:
    try:
        args = parse_args()
        if args.env_file:
            load_env_file(args.env_file)

        c = AsterV3Client(args.base_url, require_env("ASTER_USER"), require_env("ASTER_SIGNER"), require_env("ASTER_SIGNER_PRIVATE_KEY"), args.recv_window)
        code, body = c.signed_request("POST", "/fapi/v3/marginType", {"symbol": args.symbol, "marginType": args.margin_type})
        normalized_success, matched_rule, matched_message = match_noop_margin_type_rule(code, body)
        out = {"set_margin_type": format_exchange_response(code, body)}
        if normalized_success:
            out["set_margin_type"]["normalized_success"] = True
            out["set_margin_type"]["hint"] = "Margin type already set; no change required."
            out["set_margin_type"]["matched_rule"] = matched_rule
            out["set_margin_type"]["matched_message"] = matched_message
        print(json.dumps(out, ensure_ascii=False))
        return 0 if (code == 200 or normalized_success) else 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())

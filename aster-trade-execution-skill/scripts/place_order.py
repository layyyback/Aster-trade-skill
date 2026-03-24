#!/usr/bin/env python3
"""Unified order entrypoint: auto-select V3 or fallback to V1."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def read_env_file_values(path: str) -> dict:
    values = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            value = val.strip().strip("'").strip('"')
            if value == "":
                continue
            values[key] = value
    return values


def has_v3_env(env: dict) -> bool:
    return all(env.get(k, "").strip() for k in ["ASTER_USER", "ASTER_SIGNER", "ASTER_SIGNER_PRIVATE_KEY"])


def has_v1_env(env: dict) -> bool:
    return all(env.get(k, "").strip() for k in ["ASTER_API_KEY", "ASTER_SECRET_KEY"])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified Aster order entrypoint")
    p.add_argument("--version", choices=["auto", "v3", "v1"], default="auto")
    p.add_argument("--env-file", help="Optional env file path passed through to selected script")
    p.add_argument("rest", nargs=argparse.REMAINDER, help="Arguments forwarded to selected script")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    scripts_dir = Path(__file__).resolve().parent

    env = os.environ.copy()
    if args.env_file:
        try:
            env.update(read_env_file_values(args.env_file))
        except FileNotFoundError:
            print(f'{{"error":"env file not found: {args.env_file}"}}')
            return 1
    target = None

    if args.version == "v3":
        target = scripts_dir / "place_order_v3.py"
    elif args.version == "v1":
        target = scripts_dir / "place_market_order_v1.py"
    else:
        if has_v3_env(env):
            target = scripts_dir / "place_order_v3.py"
        elif has_v1_env(env):
            target = scripts_dir / "place_market_order_v1.py"
        else:
            print('{"error":"No usable credentials found: configure V3 (ASTER_USER/ASTER_SIGNER/ASTER_SIGNER_PRIVATE_KEY) or V1 (ASTER_API_KEY/ASTER_SECRET_KEY)."}')
            return 1

    cmd = [sys.executable, str(target)]
    if args.env_file:
        cmd.extend(["--env-file", args.env_file])
    if args.rest:
        forwarded = args.rest
        if forwarded and forwarded[0] == "--":
            forwarded = forwarded[1:]
        cmd.extend(forwarded)

    completed = subprocess.run(cmd, env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

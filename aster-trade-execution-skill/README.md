# Aster Trade Execution Skill

Script-first Aster Futures execution toolkit (V3 + V1), designed for safe and repeatable trade operations.

## What This Skill Provides
- V3 signed trading and account scripts
- V1 HMAC fallback scripts
- Safe-by-default execution (`dry-run` first)
- Market trade by notional or quantity
- Full lifecycle operations: place, query, cancel, batch cancel, cancel all, positions, balance, leverage, margin type, isolated margin, conditional orders, amend (cancel+replace)
- Deterministic signing normalization and fixture test

## Trigger Keywords
- `trade`
- `trading`
- `execution`
- `place trade`
- `cancel trade`
- `amend trade`
- `leverage`
- `margin`
- `position`

## Requirements
- Python 3.9+
- Aster Futures account with either:
  - V3 API wallet binding (`ASTER_USER` + `ASTER_SIGNER` + `ASTER_SIGNER_PRIVATE_KEY`), or
  - V1 API key pair (`ASTER_API_KEY` + `ASTER_SECRET_KEY`)

Install dependencies:

```bash
python3 -m pip install --user -r requirements.txt
```

## Credentials
Use one of these methods:

1. `--env-file` (recommended)

```bash
cat >/tmp/aster.env <<'EOF'
export ASTER_USER='0x...'
export ASTER_SIGNER='0x...'
export ASTER_SIGNER_PRIVATE_KEY='0x...'
EOF
chmod 600 /tmp/aster.env
```

Note: empty values in env files are ignored and will not overwrite already-exported runtime credentials.
Note: `scripts/place_order.py` reads `--env-file` for version auto-selection, so V1-only env files are supported.

2. Inline env for one-shot execution

```bash
ASTER_USER='0x...' \
ASTER_SIGNER='0x...' \
ASTER_SIGNER_PRIVATE_KEY='0x...' \
python3 scripts/place_order_v3.py --symbol BTCUSDT --side BUY --notional-usdt 100
```

V1 inline example:

```bash
ASTER_API_KEY='...' \
ASTER_SECRET_KEY='...' \
python3 scripts/place_order.py -- --symbol BTCUSDT --side BUY --notional-usdt 100 --execute
```

## Quick Start

### 1) Dry-run (default, no live order sent) via unified entrypoint

```bash
python3 scripts/place_order.py -- \
  --symbol BTCUSDT \
  --side BUY \
  --notional-usdt 100 \
  --notional-rounding ceil \
  --leverage 2 \
  --env-file /tmp/aster.env
```

### 2) Execute live order (explicit)

```bash
python3 scripts/place_order.py -- \
  --symbol BTCUSDT \
  --side BUY \
  --notional-usdt 100 \
  --notional-rounding ceil \
  --leverage 2 \
  --env-file /tmp/aster.env \
  --execute
```

Version pinning (optional):

```bash
python3 scripts/place_order.py --version v3 -- --symbol BTCUSDT --side BUY --notional-usdt 100
python3 scripts/place_order.py --version v1 -- --symbol BTCUSDT --side BUY --notional-usdt 100
```

## Notional Conversion (All Symbols)
For `--notional-usdt`, quantity is computed using each symbol's own filters (`stepSize`, `minQty`, `maxQty`, `minNotional`).

Use `--notional-rounding` to control behavior:
- `floor`: do not exceed target notional
- `ceil`: ensure at least target notional
- `nearest`: closest notional to target

This is symbol-agnostic and works the same way across all markets.

## Core Scripts
- `scripts/place_order.py`: unified entrypoint (auto-select V3 first, then V1 fallback)
- `scripts/place_order_v3.py`: unified minimal entry (dry-run by default)
- `scripts/place_market_order_v1.py`: V1 market order script (dry-run by default)
- `scripts/place_market_order_v3.py`: market order script with advanced controls
- `scripts/place_conditional_order_v3.py`: STOP/TP orders
- `scripts/query_order_v3.py`: query one order
- `scripts/query_order_v1.py`: query one order (V1)
- `scripts/cancel_order_v3.py`: cancel one order
- `scripts/cancel_order_v1.py`: cancel one order (V1)
- `scripts/cancel_batch_orders_v3.py`: batch cancel
- `scripts/cancel_all_open_orders_v3.py`: cancel all open orders for symbol
- `scripts/list_open_orders_v3.py`: list open orders
- `scripts/list_all_orders_v3.py`: list historical orders
- `scripts/get_positions_v3.py`: position risk snapshot
- `scripts/close_position_market_v3.py`: close position via reduce-only market order
- `scripts/get_balance_v3.py`: balance snapshot
- `scripts/get_balance_v1.py`: balance snapshot (V1)
- `scripts/set_leverage_v3.py`: set leverage
- `scripts/set_leverage_v1.py`: set leverage (V1)
- `scripts/set_margin_type_v3.py`: set margin type
- `scripts/modify_isolated_margin_v3.py`: modify isolated margin
- `scripts/amend_order_v3.py`: amend via cancel+replace
- `scripts/precheck_order_v3.py`: precheck quantity/notional/margin feasibility

## Validation
Run signing consistency fixture:

```bash
python3 scripts/tests/signing_consistency_test.py
```

## Safety Notes
- Do not paste private keys in chat, tickets, or source control.
- No automatic retry is performed for live trade placement paths.
- If a key is exposed: revoke API wallet, rotate signer key, rotate related keys, and audit recent activity.

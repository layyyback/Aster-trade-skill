---
name: aster-trade-execution
description: "Use when users want to place, cancel, amend, or manage Aster Futures trades and account-risk actions. Script-first workflow for V3 signing and trade execution. Do NOT use for market-only questions."
license: Apache-2.0
metadata:
  author: aster
  version: "1.5.2"
homepage: "https://www.asterdex.com"
---

# Aster Futures Trade Execution API

Trade execution only for Aster Futures. Do not answer purely market-data requests or general programming questions.

**Base URL**: `https://fapi.asterdex.com`  
**Base paths**: `/fapi/v1` and `/fapi/v3`

## Routing
- This skill is for trade/account actions only.
- Trade scope includes order placement, cancellation, amendment, leverage, margin type, and position management.
- For prices/klines/order book/funding only, use `aster-market-data`.

## Trigger Keywords
- `trade`
- `trading`
- `trade execution`
- `place trade`
- `cancel trade`
- `amend trade`
- `position`
- `leverage`
- `margin`

## Script-First Workflow (Required)
- Prefer script execution over ad-hoc request construction.
- Script set:
  - `scripts/place_order.py` (unified auto-select entrypoint: V3 first, V1 fallback)
  - `scripts/place_order_v3.py` (minimal executable entry, dry-run by default)
  - `scripts/place_market_order_v3.py`
  - `scripts/place_market_order_v1.py`
  - `scripts/place_conditional_order_v3.py`
  - `scripts/cancel_order_v3.py`
  - `scripts/cancel_all_open_orders_v3.py`
  - `scripts/cancel_batch_orders_v3.py`
  - `scripts/query_order_v3.py`
  - `scripts/query_order_v1.py`
  - `scripts/list_open_orders_v3.py`
  - `scripts/list_all_orders_v3.py`
  - `scripts/get_balance_v3.py`
  - `scripts/get_balance_v1.py`
  - `scripts/get_positions_v3.py`
  - `scripts/close_position_market_v3.py`
  - `scripts/set_leverage_v3.py`
  - `scripts/set_leverage_v1.py`
  - `scripts/set_margin_type_v3.py`
  - `scripts/modify_isolated_margin_v3.py`
  - `scripts/amend_order_v3.py`
  - `scripts/precheck_order_v3.py`
- Shared module: `scripts/v3_common.py`.
- Shared module: `scripts/v1_common.py`.
- For market trade requests, default flow is:
  1. Load credentials.
  2. Optionally set leverage.
  3. Convert notional USDT to valid `quantity` with filters.
  4. Submit market trade order.
  5. Query order and return final status.

## Authentication & Credentials
### V1 (TRADE / USER_DATA)
- Signed endpoints require `signature` and use HMAC-SHA256.
- `signature` can be sent in query string or request body.
- API key is required in the `X-MBX-APIKEY` header.

### V3 (TRADE / USER_DATA / USER_STREAM)
- Signed endpoints require `user`, `signer`, `nonce`, `signature`, `timestamp` (and optional `recvWindow`).
- Use the script's signing routine; do not improvise.
- Stable signing recipe used by this skill (normative):
  1. Build params map with string values, excluding `None`.
  2. Add `recvWindow` (string) and `timestamp` (string ms).
  3. Normalize value types:
     - `bool` -> `\"true\"` / `\"false\"`
     - `dict/list` -> compact JSON (`sort_keys=True`, separators `(',', ':')`)
     - scalar -> `str(value)`
  4. Serialize normalized params as compact sorted JSON (`json_params`).
  5. Generate `nonce` as microseconds since epoch (`uint256`).
  6. ABI encode exactly:
     - `string json_params`
     - `address user`
     - `address signer`
     - `uint256 nonce`
  7. Keccak256 hash the encoded bytes.
  8. Sign via `eth_account.messages.encode_defunct(hexstr=hash)` (EIP-191 prefix applied by `encode_defunct`).
  9. Send `signature` as `0x{r}{s}{v}` (65-byte hex). `v` is library output, no manual remapping.
  10. Submit request with `user/signer/nonce/signature`.

V3 signing test vector (fixture):
- Normalized JSON:
  - `{\"meta\":\"{\\\"a\\\":2,\\\"b\\\":1}\",\"quantity\":\"0.001\",\"recvWindow\":\"5000\",\"reduceOnly\":\"false\",\"symbol\":\"BTCUSDT\",\"tags\":\"[\\\"x\\\",{\\\"k\\\":\\\"v\\\"}]\",\"timestamp\":\"1700000000000\",\"type\":\"MARKET\"}`
- Keccak digest:
  - `a1ef644df4d4e664b37554c2b219d3bf93fb1f9af32413cdab5b62ae9098379a`
- Signature fixture example:
  - `0x391774f22aa93c372a122c3add068760f1515deb1ed743f0eed35fc94f86e8a4396b57135673f1deed95e1af2098916855db6a5bc6012dad35f5a586b69348561c`

**Never** output credentials or private keys to logs or user-visible content.

Recommended environment variables:
- `ASTER_API_KEY` (V1)
- `ASTER_SECRET_KEY` (V1 HMAC secret)
- `ASTER_USER` (V3 main account wallet)
- `ASTER_SIGNER` (V3 API wallet)
- `ASTER_SIGNER_PRIVATE_KEY` (V3 signing key)

## Session & Secrets
- Store `ASTER_API_KEY`, `ASTER_SECRET_KEY`, and `ASTER_SIGNER_PRIVATE_KEY` only in secret managers or runtime env vars.
- Never hardcode secrets in source code or commit them to Git.
- V1: pass `ASTER_API_KEY` only via `X-MBX-APIKEY`.
- V3: sign locally; never transmit private key.
- `--env-file` loader is whitelist-only for `ASTER_*` keys used by this skill.
- Use trusted env files only.
- Empty env-file values are ignored and do not override existing runtime credentials.
- If env vars are not visible in agent shell, prefer `--env-file /tmp/aster.env`:
  ```bash
  cat >/tmp/aster.env <<'EOF'
  export ASTER_USER='...'
  export ASTER_SIGNER='...'
  export ASTER_SIGNER_PRIVATE_KEY='...'
  EOF
  chmod 600 /tmp/aster.env
  ```
- Alternative inline template for one-shot process execution:
  ```bash
  ASTER_USER='...' \
  ASTER_SIGNER='...' \
  ASTER_SIGNER_PRIVATE_KEY='...' \
  python3 scripts/place_order_v3.py --symbol BTCUSDT --side BUY --notional-usdt 100
  ```
- `.env` template (never commit):
  ```bash
  ASTER_USER=0x...
  ASTER_SIGNER=0x...
  ASTER_SIGNER_PRIVATE_KEY=0x...
  ```

## Version Selection Rules
- Default: V3.
- Use V1 automatically when V3 credentials are unavailable but V1 credentials exist.
- Unified entry `scripts/place_order.py` selects V3 first, then V1 fallback.
- If the user asks for a specific version, follow it.

## Operation Flow
1. Identify intent: precheck/place/modify/cancel/close/query/risk settings.
2. Collect required parameters:
   - Place market: `symbol`, `side`, and either `notional` target or `quantity`.
   - Place conditional: `type`, `stopPrice`, plus `price` or `quantity` depending on type.
   - Optional: `leverage`, `marginType`, `positionSide`, `reduceOnly`.
3. Validate filters from `exchangeInfo`:
   - Use `MARKET_LOT_SIZE` (fallback `LOT_SIZE`) for market quantity rounding.
   - Respect `minQty`, `stepSize`, `maxQty`, and `MIN_NOTIONAL`.
4. Mandatory pre-order checks for placement:
   - Auth and balance check (`GET /fapi/v3/balance`)
   - Exchange filters (`exchangeInfo`) unless explicit advanced skip mode is used
   - Optional leverage update before order placement
5. Submit signed request.
6. Query order status and return concise execution details (`orderId`, `status`, `avgPrice`, `executedQty`, `cumQuote`).
8. For modify requests, use cancel+replace script (`amend_order_v3.py`).
9. For exit flows, prefer `close_position_market_v3.py` with `reduceOnly=true`.

Failure mapping and retry policy:
- Auth/balance failure: stop; do not auto-retry.
- Filter/validation failure: stop; correct inputs and rerun.
- Leverage setting failure: stop and surface exchange error.
- Order placement failure: stop; no automatic retry on trade placement paths.

## Error Handling (Required)
- `-1000 No agent found`:
  - Meaning: user/signer not properly bound on exchange side.
  - Action: ask user to complete API wallet/agent binding, then retry.
- `-1000 Signature check failed`:
  - Meaning: signing algorithm or payload mismatch.
  - Action: use script signing only; verify correct env vars and timestamp drift.
- `-1102 mandatory parameter ... malformed`:
  - Meaning: missing/unsupported param (often `quoteOrderQty` path).
  - Action: compute and send `quantity` instead.
- `-2019 Margin is insufficient`:
  - Action: query `/fapi/v3/balance`, return available margin, ask user to transfer funds or reduce size.
- `-1021 timestamp outside recvWindow`:
  - Action: verify system time and retry with low latency path.

## CLI Usage
Install dependencies once:
```bash
python3 -m pip install --user -r requirements.txt
```

Recommended minimal executable entry (dry-run by default):
```bash
python3 scripts/place_order_v3.py \
  --symbol BTCUSDT \
  --side BUY \
  --notional-usdt 100 \
  --notional-rounding ceil \
  --leverage 2 \
  --env-file /tmp/aster.env
```

Execute real order explicitly:
```bash
python3 scripts/place_order_v3.py \
  --symbol BTCUSDT \
  --side BUY \
  --notional-usdt 100 \
  --notional-rounding ceil \
  --leverage 2 \
  --env-file /tmp/aster.env \
  --execute
```

Market order by notional with leverage (legacy script):
```bash
python3 scripts/place_market_order_v3.py \
  --symbol BTCUSDT \
  --side BUY \
  --notional-usdt 100 \
  --notional-rounding ceil \
  --leverage 2 \
  --env-file /tmp/aster.env
```

Advanced fast path (skip prefetch; requires explicit quantity and accepts validation risk):
```bash
python3 scripts/place_market_order_v3.py \
  --symbol BTCUSDT \
  --side BUY \
  --quantity 0.001 \
  --skip-prefetch \
  --env-file /tmp/aster.env
```

Set leverage only:
```bash
python3 scripts/set_leverage_v3.py \
  --symbol BTCUSDT \
  --leverage 3 \
  --env-file /tmp/aster.env
```

Query order:
```bash
python3 scripts/query_order_v3.py \
  --symbol BTCUSDT \
  --order-id 123456789 \
  --env-file /tmp/aster.env
```

Cancel order:
```bash
python3 scripts/cancel_order_v3.py \
  --symbol BTCUSDT \
  --order-id 123456789 \
  --env-file /tmp/aster.env
```

Check balance:
```bash
python3 scripts/get_balance_v3.py \
  --asset USDT \
  --env-file /tmp/aster.env
```

List open orders:
```bash
python3 scripts/list_open_orders_v3.py \
  --symbol BTCUSDT \
  --env-file /tmp/aster.env
```

List all orders:
```bash
python3 scripts/list_all_orders_v3.py \
  --symbol BTCUSDT \
  --limit 50 \
  --env-file /tmp/aster.env
```

Get positions:
```bash
python3 scripts/get_positions_v3.py \
  --symbol BTCUSDT \
  --non-zero-only \
  --env-file /tmp/aster.env
```

Cancel all open orders:
```bash
python3 scripts/cancel_all_open_orders_v3.py \
  --symbol BTCUSDT \
  --env-file /tmp/aster.env
```

Batch cancel:
```bash
python3 scripts/cancel_batch_orders_v3.py \
  --symbol BTCUSDT \
  --order-ids 111,222,333 \
  --env-file /tmp/aster.env
```

Close position at market:
```bash
python3 scripts/close_position_market_v3.py \
  --symbol BTCUSDT \
  --position-side BOTH \
  --env-file /tmp/aster.env
```

Set margin type:
```bash
python3 scripts/set_margin_type_v3.py \
  --symbol BTCUSDT \
  --margin-type ISOLATED \
  --env-file /tmp/aster.env
```

Modify isolated margin:
```bash
python3 scripts/modify_isolated_margin_v3.py \
  --symbol BTCUSDT \
  --amount 10 \
  --type 1 \
  --position-side BOTH \
  --env-file /tmp/aster.env
```

Place conditional stop order:
```bash
python3 scripts/place_conditional_order_v3.py \
  --symbol BTCUSDT \
  --side SELL \
  --type STOP_MARKET \
  --stop-price 70000 \
  --quantity 0.001 \
  --position-side BOTH \
  --env-file /tmp/aster.env
```

Amend order via cancel+replace:
```bash
python3 scripts/amend_order_v3.py \
  --symbol BTCUSDT \
  --order-id 123456789 \
  --new-price 72000 \
  --new-quantity 0.001 \
  --env-file /tmp/aster.env
```

Precheck before placing:
```bash
python3 scripts/precheck_order_v3.py \
  --symbol BTCUSDT \
  --side BUY \
  --notional-usdt 100 \
  --leverage 2 \
  --env-file /tmp/aster.env
```

All scripts output machine-readable JSON and default to compact fields.

Notional conversion rules (normative):
- `quantity = floor((notional / reference_price) to stepSize)`
- If `quantity < minQty`, set `quantity = minQty`
- Reject if `quantity > maxQty`
- Reject if `quantity * reference_price < minNotional`
- Rounding strategy is configurable via `--notional-rounding`:
  - `floor`: do not exceed target notional (may be significantly below target for coarse step sizes)
  - `ceil`: ensure at least target notional (may exceed target)
  - `nearest`: closest notional distance to target
- This behavior is symbol-agnostic and applies to all symbols according to each symbol's `stepSize/minQty/maxQty/minNotional`.

Run signing consistency fixture test:
```bash
python3 scripts/tests/signing_consistency_test.py
```

Direction and risk defaults:
- `--side` is mandatory for place-order scripts (`BUY` or `SELL` only).
- `--position-side` defaults to `BOTH`.
- `--reduce-only` defaults to `false`; enable explicitly for risk-reduction intent.
- Close-position script derives side from live position if `--side` is not provided.

Real-order protection:
- `scripts/place_order_v3.py` defaults to dry-run.
- Real placement requires explicit `--execute`.
- Dry-run prints planned params and checks without sending order.

Security incident response:
- Do not paste private keys in chat or ticket systems.
- If key leakage is suspected:
  1. Revoke/disable the affected API wallet immediately.
  2. Rotate `ASTER_SIGNER_PRIVATE_KEY` and rebind signer.
  3. Rotate related API keys/secrets.
  4. Review recent account/order activity for unauthorized actions.

## Endpoint Index (V1)
Core order paths:
- `POST /fapi/v1/order` (New Order)
- `GET /fapi/v1/order` (Query Order)
- `DELETE /fapi/v1/order` (Cancel Order)

Additional trading / user data endpoints exist for:
- New Order
- Place Multiple Orders
- Query Order
- Cancel Order
- Cancel All Open Orders
- Cancel Multiple Orders
- Query Current Open Order
- Current All Open Orders
- All Orders
- Change Initial Leverage
- Change Margin Type
- Modify Isolated Position Margin
- Position Information
- Account Balance
- Account Information
- User Data Stream (start / keepalive / close)

## Endpoint Index (V3)
Core order paths:
- `POST /fapi/v3/order` (New Order)
- `GET /fapi/v3/order` (Query Order)
- `DELETE /fapi/v3/order` (Cancel Order)

Additional paths used by bundled scripts:
- `GET /fapi/v3/openOrders`
- `GET /fapi/v3/allOrders`
- `DELETE /fapi/v3/allOpenOrders`
- `DELETE /fapi/v3/batchOrders`
- `GET /fapi/v3/positionRisk`
- `POST /fapi/v3/leverage`
- `POST /fapi/v3/marginType`
- `POST /fapi/v3/positionMargin`
- `GET /fapi/v3/balance`

## Examples
- "Open a BTCUSDT market long for 100 USDT notional with 2x leverage."
- "Set BTCUSDT leverage to 3x, then place a 50 USDT market short."
- "Query the latest order and return final avg price and executed quantity."

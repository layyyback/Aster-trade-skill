---
name: aster-market-data
description: "Use when users want to query Aster Futures market data: prices, klines, depth, funding rates, exchange info, and trades. All public endpoints, no authentication required. Do NOT use for trade execution or account operations."
license: Apache-2.0
metadata:
  author: aster
  version: "1.0.0"
homepage: "https://www.asterdex.com"
---

# Aster Futures Market Data API

Market data queries only for Aster Futures. Do not handle trade execution, account operations, or position management.

**Base URL**: `https://fapi.asterdex.com`
**Base path**: `/fapi/v3`

## Routing
- This skill is for public market data queries only.
- Market data scope includes prices, tickers, order book, klines, funding rates, trades, and exchange info.
- For trade execution, leverage, margin, or position management, use `aster-trade-execution`.

## Trigger Keywords
- `price`
- `ticker`
- `kline`
- `candlestick`
- `depth`
- `order book`
- `funding rate`
- `mark price`
- `index price`
- `market data`
- `trades`
- `exchange info`
- `volume`

## Script-First Workflow (Required)
- Prefer script execution over ad-hoc request construction.
- Script set:
  - `scripts/get_price.py` (latest price, single or all symbols)
  - `scripts/get_ticker_24hr.py` (24h price change statistics)
  - `scripts/get_book_ticker.py` (best bid/ask price and quantity)
  - `scripts/get_depth.py` (order book depth)
  - `scripts/get_klines.py` (kline/candlestick data)
  - `scripts/get_mark_price_klines.py` (mark price klines)
  - `scripts/get_index_price_klines.py` (index price klines)
  - `scripts/get_mark_price.py` (mark price + funding rate + index price)
  - `scripts/get_funding_rate.py` (funding rate history)
  - `scripts/get_funding_info.py` (funding rate config: interval, cap, floor)
  - `scripts/get_recent_trades.py` (recent market trades)
  - `scripts/get_agg_trades.py` (compressed/aggregate trades)
  - `scripts/get_exchange_info.py` (trading rules, symbol info, filters)
  - `scripts/ping.py` (connectivity test)
  - `scripts/get_server_time.py` (server time)
  - `scripts/get_index_references.py` (index price source exchanges and weights)
- Shared module: `scripts/market_common.py`

## Authentication
None required. All endpoints are public.

## CLI Usage

Install dependencies:
```bash
python3 -m pip install --user -r requirements.txt
```

### Price Queries

Latest price (single symbol):
```bash
python3 scripts/get_price.py --symbol BTCUSDT
```

Latest price (all symbols):
```bash
python3 scripts/get_price.py
```

24h ticker stats:
```bash
python3 scripts/get_ticker_24hr.py --symbol BTCUSDT
```

Best bid/ask:
```bash
python3 scripts/get_book_ticker.py --symbol BTCUSDT
```

### Order Book

```bash
python3 scripts/get_depth.py --symbol BTCUSDT --limit 20
```

### Klines

Standard klines:
```bash
python3 scripts/get_klines.py --symbol BTCUSDT --interval 1h --limit 10
```

Mark price klines:
```bash
python3 scripts/get_mark_price_klines.py --symbol BTCUSDT --interval 1h --limit 10
```

Index price klines:
```bash
python3 scripts/get_index_price_klines.py --pair BTCUSDT --interval 1h --limit 10
```

### Mark Price & Funding

Mark price + current funding rate:
```bash
python3 scripts/get_mark_price.py --symbol BTCUSDT
```

Funding rate history:
```bash
python3 scripts/get_funding_rate.py --symbol BTCUSDT --limit 10
```

Funding rate config:
```bash
python3 scripts/get_funding_info.py --symbol BTCUSDT
```

### Trades

Recent trades:
```bash
python3 scripts/get_recent_trades.py --symbol BTCUSDT --limit 10
```

Aggregate trades:
```bash
python3 scripts/get_agg_trades.py --symbol BTCUSDT --limit 10
```

### Exchange Info

All symbols:
```bash
python3 scripts/get_exchange_info.py
```

Single symbol (filtered):
```bash
python3 scripts/get_exchange_info.py --symbol BTCUSDT
```

### Connectivity & Time

```bash
python3 scripts/ping.py
python3 scripts/get_server_time.py
```

### Index Price References

```bash
python3 scripts/get_index_references.py --symbol BTCUSDT
```

## Endpoint Index

| Endpoint | Description | Script |
|----------|-------------|--------|
| `GET /fapi/v3/ticker/price` | Latest price | `get_price.py` |
| `GET /fapi/v3/ticker/24hr` | 24h stats | `get_ticker_24hr.py` |
| `GET /fapi/v3/ticker/bookTicker` | Best bid/ask | `get_book_ticker.py` |
| `GET /fapi/v3/depth` | Order book | `get_depth.py` |
| `GET /fapi/v3/klines` | Klines | `get_klines.py` |
| `GET /fapi/v3/markPriceKlines` | Mark price klines | `get_mark_price_klines.py` |
| `GET /fapi/v3/indexPriceKlines` | Index price klines | `get_index_price_klines.py` |
| `GET /fapi/v3/premiumIndex` | Mark price + funding | `get_mark_price.py` |
| `GET /fapi/v3/fundingRate` | Funding rate history | `get_funding_rate.py` |
| `GET /fapi/v3/fundingInfo` | Funding rate config | `get_funding_info.py` |
| `GET /fapi/v3/trades` | Recent trades | `get_recent_trades.py` |
| `GET /fapi/v3/aggTrades` | Aggregate trades | `get_agg_trades.py` |
| `GET /fapi/v3/exchangeInfo` | Exchange info | `get_exchange_info.py` |
| `GET /fapi/v3/ping` | Connectivity test | `ping.py` |
| `GET /fapi/v3/time` | Server time | `get_server_time.py` |
| `GET /fapi/v3/indexPriceReferences` | Index price sources | `get_index_references.py` |

All scripts output machine-readable JSON and return exit code 0 on success, 1 on failure.

## Examples
- "What's the current BTCUSDT price?"
- "Show me the 1h klines for ETHUSDT."
- "What's the current funding rate for BTCUSDT?"
- "Show the order book depth for SOLUSDT."
- "List all trading pairs on Aster."

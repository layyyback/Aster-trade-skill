# Aster Trade Skills

**[中文版](README_CN.md)**

A collection of automation tools for the Aster Futures API, comprising three independent Skills: Trade Execution, Market Data, and Volume Anomaly Monitor.

All Skills follow the [AgentSkills](https://agentskills.io) format and are compatible with [Claude Code](https://claude.ai/claude-code), [OpenClaw](https://github.com/openclaw/openclaw), and other AI Agent platforms.

## Structure

```
├── api-docs/                         # Official Aster API docs (V1/V3, Spot/Futures)
├── aster-trade-execution-skill/      # Trade Execution Skill
├── aster-market-data-skill/          # Market Data Skill
└── aster-volume-monitor-skill/       # Volume Anomaly Monitor Skill
```

---

## 1. aster-trade-execution-skill — Trade Execution

Place, cancel, amend orders, manage leverage, margin, and positions. Supports both V3 (Web3 signing) and V1 (HMAC).

**Features:**
- Market / Limit / Conditional / Trailing Stop orders
- Single and batch cancel
- Amend orders (cancel + replace)
- Leverage, margin type, isolated margin adjustment
- Position, balance, and order queries
- Market close position
- Pre-order validation (precheck)

**Quick Start:**
```bash
cd aster-trade-execution-skill
python3 -m pip install --user -r requirements.txt

# Dry-run (no real order)
python3 scripts/place_order_v3.py \
  --symbol BTCUSDT --side BUY --notional-usdt 100 \
  --env-file /tmp/aster.env

# Execute real order
python3 scripts/place_order_v3.py \
  --symbol BTCUSDT --side BUY --notional-usdt 100 \
  --env-file /tmp/aster.env --execute
```

**Authentication:**

| Version | Method | Env Vars |
|---------|--------|----------|
| V3 | Web3 Signing (EIP-191) | `ASTER_USER`, `ASTER_SIGNER`, `ASTER_SIGNER_PRIVATE_KEY` |
| V1 | HMAC-SHA256 | `ASTER_API_KEY`, `ASTER_SECRET_KEY` |

See [aster-trade-execution-skill/SKILL.md](aster-trade-execution-skill/SKILL.md) for full details.

---

## 2. aster-market-data-skill — Market Data

Covers 16 public API endpoints. No authentication required.

**Endpoints:**

| Feature | Script |
|---------|--------|
| Latest Price | `get_price.py` |
| 24h Ticker Stats | `get_ticker_24hr.py` |
| Best Bid/Ask | `get_book_ticker.py` |
| Order Book Depth | `get_depth.py` |
| Klines | `get_klines.py` |
| Mark Price Klines | `get_mark_price_klines.py` |
| Index Price Klines | `get_index_price_klines.py` |
| Mark Price + Funding Rate | `get_mark_price.py` |
| Funding Rate History | `get_funding_rate.py` |
| Funding Rate Config | `get_funding_info.py` |
| Recent Trades | `get_recent_trades.py` |
| Aggregate Trades | `get_agg_trades.py` |
| Exchange Info / Filters | `get_exchange_info.py` |
| Connectivity Test | `ping.py` |
| Server Time | `get_server_time.py` |
| Index Price References | `get_index_references.py` |

**Quick Start:**
```bash
cd aster-market-data-skill
python3 -m pip install --user -r requirements.txt

python3 scripts/get_price.py --symbol BTCUSDT
python3 scripts/get_klines.py --symbol ETHUSDT --interval 1h --limit 10
python3 scripts/get_depth.py --symbol SOLUSDT --limit 20
python3 scripts/get_funding_rate.py --symbol BTCUSDT --limit 5
```

See [aster-market-data-skill/SKILL.md](aster-market-data-skill/SKILL.md) for full details.

---

## 3. aster-volume-monitor-skill — Volume Anomaly Monitor

Detects abnormal volume spikes on Aster Futures. Outputs JSON for OpenClaw or other Agent platforms to consume and forward.

**How it works:**
1. Fetches the last N klines for a symbol
2. Computes period-over-period ratio using **base asset volume** (not USDT, to avoid price interference)
3. Ratio >= threshold → flagged as anomaly
4. Periods below the USDT notional floor are skipped (filters out low-volume noise)

**Parameters:**

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--symbol` | Trading pair | Required |
| `--interval` | Kline interval | `15m` |
| `--lookback` | Number of klines to analyze | `10` |
| `--ratio-threshold` | Anomaly ratio threshold | `2.0` |
| `--min-notional` | Minimum USDT volume to trigger detection | `100000` |
| `--output-file` | Append anomaly records to file (JSON Lines) | None |

**Quick Start:**
```bash
cd aster-volume-monitor-skill
python3 -m pip install --user -r requirements.txt

# Monitor all symbols
python3 scripts/detect_volume_anomaly.py

# Exclude specific symbols
python3 scripts/detect_volume_anomaly.py --exclude USDCUSDT,TUSDUSDT

# Monitor specific symbols only
python3 scripts/detect_volume_anomaly.py --symbol BTCUSDT,ETHUSDT,SOLUSDT
```

See [aster-volume-monitor-skill/SKILL.md](aster-volume-monitor-skill/SKILL.md) for full details.

---

## OpenClaw Integration

All Skills are compatible with [OpenClaw](https://github.com/openclaw/openclaw) AgentSkills format.

Install to OpenClaw:
```bash
# Global (available to all agents)
cp -r aster-market-data-skill ~/.openclaw/skills/aster-market-data
cp -r aster-volume-monitor-skill ~/.openclaw/skills/aster-volume-monitor

# Or workspace-level
cp -r aster-market-data-skill <workspace>/skills/aster-market-data
```

Volume monitor cron config (`openclaw.json`):
```json
{
  "cron": [
    {
      "schedule": "*/15 * * * *",
      "message": "Run volume anomaly detection: python3 {baseDir}/scripts/detect_volume_anomaly.py --exclude USDCUSDT"
    }
  ]
}
```

---

## API Docs

The `api-docs/` directory contains official Aster API documentation:

- V1 / V3 Futures API (EN & CN)
- Spot API (EN & CN)
- Testnet API
- API Key Registration
- Deposit & Withdrawal API
- V1 vs V3 Comparison
- Signing Demos (Python / Go / JS)

---

## Security

- **Never** hardcode private keys or API keys in code or Git
- Use environment variables or `--env-file` to pass credentials
- Add env files to `.gitignore`
- If key leakage is suspected, revoke and rotate immediately on the Aster platform

## License

Apache-2.0

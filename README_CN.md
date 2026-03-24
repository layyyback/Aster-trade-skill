# Aster Trade Skills

**[English](README.md)**

Aster Futures API 的自动化交易工具集，包含三个独立 Skill：交易执行、市场数据查询、交易量异常监控。

所有 Skill 均兼容 [AgentSkills](https://agentskills.io) 格式，可直接用于 [Claude Code](https://claude.ai/claude-code)、[OpenClaw](https://github.com/openclaw/openclaw) 等 AI Agent 平台。

## 目录结构

```
├── api-docs/                         # Aster 官方 API 文档（V1/V3/Spot/Futures）
├── aster-trade-execution-skill/      # 交易执行 Skill
├── aster-market-data-skill/          # 市场数据 Skill
└── aster-volume-monitor-skill/       # 交易量异常监控 Skill
```

---

## 1. aster-trade-execution-skill — 交易执行

下单、撤单、改单、杠杆、保证金、仓位管理。支持 V3（Web3 签名）和 V1（HMAC）双版本。

**功能覆盖：**
- 市价 / 限价 / 条件单 / 追踪止损单下单
- 单笔 / 批量撤单
- 改单（cancel + replace）
- 杠杆设置、保证金类型切换、逐仓保证金调整
- 持仓查询、余额查询、订单查询
- 市价平仓
- 下单前预检（precheck）

**快速使用：**
```bash
cd aster-trade-execution-skill
python3 -m pip install --user -r requirements.txt

# 干跑模式（不实际下单）
python3 scripts/place_order_v3.py \
  --symbol BTCUSDT --side BUY --notional-usdt 100 \
  --env-file /tmp/aster.env

# 实际下单
python3 scripts/place_order_v3.py \
  --symbol BTCUSDT --side BUY --notional-usdt 100 \
  --env-file /tmp/aster.env --execute
```

**认证方式：**

| 版本 | 认证 | 环境变量 |
|------|------|----------|
| V3 | Web3 签名（EIP-191） | `ASTER_USER`, `ASTER_SIGNER`, `ASTER_SIGNER_PRIVATE_KEY` |
| V1 | HMAC-SHA256 | `ASTER_API_KEY`, `ASTER_SECRET_KEY` |

详见 [aster-trade-execution-skill/SKILL.md](aster-trade-execution-skill/SKILL.md)

---

## 2. aster-market-data-skill — 市场数据查询

覆盖 16 个公共 API 端点，无需认证。

**功能覆盖：**

| 功能 | 脚本 |
|------|------|
| 最新价格 | `get_price.py` |
| 24h 涨跌统计 | `get_ticker_24hr.py` |
| 最优买卖挂单 | `get_book_ticker.py` |
| 订单簿深度 | `get_depth.py` |
| K 线 | `get_klines.py` |
| 标记价 K 线 | `get_mark_price_klines.py` |
| 指数价 K 线 | `get_index_price_klines.py` |
| 标记价 + 资金费率 | `get_mark_price.py` |
| 资金费率历史 | `get_funding_rate.py` |
| 资金费率配置 | `get_funding_info.py` |
| 最近成交 | `get_recent_trades.py` |
| 聚合成交 | `get_agg_trades.py` |
| 交易规则 / Filters | `get_exchange_info.py` |
| 连通性测试 | `ping.py` |
| 服务器时间 | `get_server_time.py` |
| 指数价成分 | `get_index_references.py` |

**快速使用：**
```bash
cd aster-market-data-skill
python3 -m pip install --user -r requirements.txt

python3 scripts/get_price.py --symbol BTCUSDT
python3 scripts/get_klines.py --symbol ETHUSDT --interval 1h --limit 10
python3 scripts/get_depth.py --symbol SOLUSDT --limit 20
python3 scripts/get_funding_rate.py --symbol BTCUSDT --limit 5
```

详见 [aster-market-data-skill/SKILL.md](aster-market-data-skill/SKILL.md)

---

## 3. aster-volume-monitor-skill — 交易量异常监控

检测 Aster Futures 单币种的交易量异常放量，支持 Telegram 推送。

**检测原理：**
1. 拉取最近 N 根 K 线
2. 用**币本位交易量**（非 USDT，避免价格波动干扰）做环比
3. 环比 >= 阈值 → 异常
4. USDT 交易量低于门槛 → 跳过（过滤低量噪音）

**可配置参数：**

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--symbol` | 交易对 | 必填 |
| `--interval` | K线周期 | `15m` |
| `--lookback` | 回看K线数量 | `10` |
| `--ratio-threshold` | 环比异常倍数阈值 | `2.0` |
| `--min-notional` | 最低 USDT 交易量门槛 | `100000` |
| `--output-file` | 追加异常记录到文件 | 无 |

**快速使用：**
```bash
cd aster-volume-monitor-skill
python3 -m pip install --user -r requirements.txt

# 单次检测
python3 scripts/detect_volume_anomaly.py --symbol BTCUSDT

# 带 TG 推送
TG_BOT_TOKEN=xxx TG_CHAT_ID=yyy \
python3 scripts/detect_volume_anomaly.py --symbol BTCUSDT

# Cron 每15分钟监控
*/15 * * * * cd /path/to/skill && python3 scripts/detect_volume_anomaly.py --symbol BTCUSDT
```

**Telegram 推送消息示例：**
```
⚠️ BTCUSDT 交易量异常

时间: 2026-03-24 10:15 UTC
周期: 15m
币本位交易量: 234.56
上一周期: 45.67
环比: 5.13x (阈值: 2.0x)
USDT交易量: $16,654,321.00
成交笔数: 3,456
```

详见 [aster-volume-monitor-skill/SKILL.md](aster-volume-monitor-skill/SKILL.md)

---

## OpenClaw 集成

所有 Skill 兼容 [OpenClaw](https://github.com/openclaw/openclaw) AgentSkills 格式。

安装到 OpenClaw：
```bash
# 全局（所有 agent 可用）
cp -r aster-market-data-skill ~/.openclaw/skills/aster-market-data
cp -r aster-volume-monitor-skill ~/.openclaw/skills/aster-volume-monitor

# 或 workspace 级别
cp -r aster-market-data-skill <workspace>/skills/aster-market-data
```

交易量监控 cron 配置（`openclaw.json`）：
```json
{
  "skills": {
    "entries": {
      "aster-volume-monitor": {
        "env": {
          "TG_BOT_TOKEN": "your-bot-token",
          "TG_CHAT_ID": "your-chat-id"
        }
      }
    }
  },
  "cron": [
    {
      "schedule": "*/15 * * * *",
      "message": "运行 BTCUSDT 交易量异常检测",
      "channel": "telegram"
    }
  ]
}
```

---

## API 文档

`api-docs/` 目录包含 Aster 官方 API 文档：

- V1 / V3 Futures API（中英文）
- Spot API（中英文）
- Testnet API
- API Key 注册说明
- 充值提现 API
- V1 vs V3 对比说明
- 签名 Demo（Python / Go / JS）

---

## 安全提醒

- **永远不要**在代码或 Git 中硬编码私钥和 API Key
- 使用环境变量或 `--env-file` 传入凭证
- env 文件加入 `.gitignore`
- 如怀疑密钥泄露，立即在 Aster 平台撤销并轮换

## License

Apache-2.0

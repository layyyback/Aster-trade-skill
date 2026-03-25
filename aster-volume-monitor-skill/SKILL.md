---
name: aster-volume-monitor
description: "监控 Aster Futures 交易量异常：基于 K 线环比检测异常放量，支持 Telegram 推送。不处理交易执行或账户操作。"
license: Apache-2.0
metadata: {"openclaw": {"requires": {"bins": ["python3"]}, "primaryEnv": "TG_BOT_TOKEN"}}
homepage: "https://www.asterdex.com"
---

# Aster Futures 交易量异常监控

检测单个币种在 Aster Futures Perps 上的交易量异常放量，基于 K 线数据环比分析。

**Base URL**: `https://fapi.asterdex.com`

## Routing
- 本 skill 仅用于交易量异常检测和推送通知。
- 价格/K线/深度等通用市场数据查询，使用 `aster-market-data`。
- 交易执行/仓位管理，使用 `aster-trade-execution`。

## Trigger Keywords
- `volume`
- `交易量`
- `放量`
- `异常`
- `监控`
- `volume spike`
- `volume anomaly`

## 检测原理

1. 从 `GET /fapi/v3/klines` 拉取最近 N+1 根 K 线
2. 对每根 K 线，用**币本位交易量**（base asset volume）与前一根做环比
3. 环比 = 当前周期币本位交易量 / 上一周期币本位交易量
4. 仅当该周期 **USDT 交易量 >= 最低门槛** 时才参与检测（过滤低量噪音）
5. 环比 >= 阈值 → 标记为异常
6. 有异常且配置了 TG → 推送到 Telegram

**为什么用币本位而非 USDT？**
避免价格波动干扰交易量对比。币本位交易量纯粹反映交易活跃度。

## 可配置参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--symbol` | 监控的交易对，逗号分隔多个。不传则监控所有 TRADING 状态的 symbol | 全部 |
| `--exclude` | 排除的交易对，逗号分隔。仅在未指定 --symbol 时生效 | 无 |
| `--interval` | K线周期，如 15m / 1h / 4h | `15m` |
| `--lookback` | 回看K线数量，越大覆盖时间越长 | `10` |
| `--ratio-threshold` | 环比异常倍数阈值。2.0 = 当前周期交易量 >= 上一周期 2 倍即异常 | `2.0` |
| `--min-notional` | 最低 USDT 交易量门槛。低于此值的周期跳过，避免低量噪音误报 | `100000` |
| `--output-file` | 可选，追加异常记录到本地文件（JSON Lines 格式），方便跨次运行追踪 | 无 |
| `--delay` | 每个 symbol 请求间隔秒数，避免触发限频 | `0.1` |
| `--silent` | 无异常时不推送 TG（默认开启） | 开启 |
| `--no-silent` | 无异常时也推送 TG 汇总 | — |
| `--base-url` | API 地址 | `https://fapi.asterdex.com` |

## 输出字段说明

| 字段 | 说明 |
|------|------|
| `interval` | K线周期 |
| `ratio_threshold` | 设定的环比异常阈值 |
| `min_notional` | 设定的最低 USDT 交易量门槛 |
| `lookback` | 回看K线数量 |
| `symbols_checked` | 本次检测的 symbol 总数 |
| `anomalies_found` | 发现的异常总条数 |
| `anomaly_symbols` | 有异常的 symbol 列表及各自异常条数 |
| `anomalies` | 所有异常详情数组 |
| `anomalies[].symbol` | 交易对 |
| `anomalies[].open_time` | 该K线开盘时间（UTC） |
| `anomalies[].volume` | 该周期币本位交易量（用于环比计算） |
| `anomalies[].quote_volume` | 该周期 USDT 交易量（用于门槛过滤） |
| `anomalies[].trades` | 该周期成交笔数 |
| `anomalies[].prev_volume` | 上一周期币本位交易量 |
| `anomalies[].ratio` | 环比倍数 = volume / prev_volume |
| `errors` | 请求失败的 symbol 及错误信息（如有） |
| `tg_push.sent` | 是否发送了 TG 消息 |
| `tg_push.ok` | TG API 返回是否成功 |
| `tg_push.reason` | 未发送的原因（no_tg_config / no_anomaly_silent） |

## Telegram 推送配置

通过环境变量配置：

| 环境变量 | 说明 |
|----------|------|
| `TG_BOT_TOKEN` | Telegram Bot Token（从 @BotFather 获取） |
| `TG_CHAT_ID` | 接收消息的 Chat ID（个人或群组） |

未配置时脚本正常运行，只输出 JSON 不推送。

## CLI 用法

安装依赖：
```bash
python3 -m pip install --user -r requirements.txt
```

### 监控所有 symbol（默认）

```bash
python3 scripts/detect_volume_anomaly.py
```

### 排除指定 symbol

```bash
python3 scripts/detect_volume_anomaly.py --exclude USDCUSDT,TUSDUSDT
```

### 只监控指定 symbol

```bash
python3 scripts/detect_volume_anomaly.py --symbol BTCUSDT,ETHUSDT,SOLUSDT
```

### 自定义参数

```bash
python3 scripts/detect_volume_anomaly.py \
  --symbol ETHUSDT \
  --interval 1h \
  --lookback 24 \
  --ratio-threshold 3.0 \
  --min-notional 500000
```

### 带 TG 推送

```bash
TG_BOT_TOKEN=123456:ABC-DEF \
TG_CHAT_ID=987654321 \
python3 scripts/detect_volume_anomaly.py
```

### 追加记录到文件

```bash
python3 scripts/detect_volume_anomaly.py \
  --output-file /tmp/volume_anomalies.jsonl
```

### Cron 持续监控（每15分钟）

```bash
*/15 * * * * cd /path/to/aster-volume-monitor-skill && TG_BOT_TOKEN=xxx TG_CHAT_ID=yyy python3 scripts/detect_volume_anomaly.py >> /var/log/volume-monitor.log 2>&1
```

## OpenClaw 安装

将本目录复制到 OpenClaw skills 目录：
```bash
cp -r aster-volume-monitor-skill ~/.openclaw/skills/aster-volume-monitor
```

或在 workspace 中：
```bash
cp -r aster-volume-monitor-skill <workspace>/skills/aster-volume-monitor
```

OpenClaw 会自动识别并加载。需要在 `openclaw.json` 中配置 TG 环境变量：
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
  }
}
```

### OpenClaw Cron 定时监控

OpenClaw 自带 cron 能力，无需系统 crontab。在 `openclaw.json` 中配置定时任务：

```json
{
  "cron": [
    {
      "schedule": "*/15 * * * *",
      "message": "运行 BTCUSDT 15分钟交易量异常检测：python3 {baseDir}/scripts/detect_volume_anomaly.py --symbol BTCUSDT --interval 15m --ratio-threshold 2.0 --min-notional 100000",
      "channel": "telegram"
    }
  ]
}
```

多币种监控：

```json
{
  "cron": [
    {
      "schedule": "*/15 * * * *",
      "message": "运行交易量异常检测：python3 {baseDir}/scripts/detect_volume_anomaly.py --symbol BTCUSDT",
      "channel": "telegram"
    },
    {
      "schedule": "*/15 * * * *",
      "message": "运行交易量异常检测：python3 {baseDir}/scripts/detect_volume_anomaly.py --symbol ETHUSDT",
      "channel": "telegram"
    },
    {
      "schedule": "*/60 * * * *",
      "message": "运行交易量异常检测：python3 {baseDir}/scripts/detect_volume_anomaly.py --symbol SOLUSDT --interval 1h --ratio-threshold 3.0",
      "channel": "telegram"
    }
  ]
}
```

`{baseDir}` 会被 OpenClaw 自动替换为 skill 目录路径。

## Examples
- "监控 BTCUSDT 15分钟交易量异常"
- "检测 ETHUSDT 是否有放量，阈值3倍"
- "查看 SOLUSDT 最近10个小时K线的交易量环比"

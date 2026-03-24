#!/usr/bin/env python3
"""
Aster Futures 交易量异常检测脚本

从 K 线数据中检测环比交易量异常，可选推送到 Telegram。

K 线字段映射:
  [0]  Open time (ms)
  [1]  Open price
  [2]  High price
  [3]  Low price
  [4]  Close price
  [5]  Volume          — 币本位交易量（用于环比计算）
  [6]  Close time (ms)
  [7]  Quote volume    — USDT 交易量（用于最低门槛过滤）
  [8]  Number of trades — 成交笔数
"""

import argparse
import json
import sys
from decimal import Decimal

from monitor_common import (
    AsterMarketClient,
    format_number,
    get_tg_notifier,
    ms_to_iso,
    output_error,
    output_json,
)

INTERVALS = [
    "1m", "3m", "5m", "15m", "30m",
    "1h", "2h", "4h", "6h", "8h", "12h",
    "1d", "3d", "1w", "1M",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="检测 Aster Futures 交易量异常")
    p.add_argument("--symbol", required=True, help="交易对，如 BTCUSDT")
    p.add_argument("--interval", default="15m", choices=INTERVALS, help="K线周期（默认 15m）")
    p.add_argument("--lookback", type=int, default=10, help="回看K线数量，越大覆盖时间越长（默认 10）")
    p.add_argument("--ratio-threshold", type=float, default=2.0, help="环比异常倍数阈值，如 2.0 表示当前周期 >= 前一周期的 2 倍即为异常（默认 2.0）")
    p.add_argument("--min-notional", type=float, default=100000, help="最低 USDT 交易量门槛，低于此值的周期跳过检测（默认 100000）")
    p.add_argument("--output-file", help="可选：追加异常记录到本地文件（JSON Lines 格式）")
    p.add_argument("--silent", action="store_true", default=True, help="无异常时不推送 TG（默认开启）")
    p.add_argument("--no-silent", action="store_false", dest="silent", help="无异常时也推送 TG 汇总")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    return p.parse_args()


def build_tg_message(symbol: str, interval: str, anomalies: list[dict]) -> str:
    """构造 Telegram 推送消息（HTML 格式）。"""
    lines = [f"⚠️ <b>{symbol} 交易量异常</b>\n"]
    for a in anomalies:
        lines.append(
            f"<b>时间:</b> {a['open_time']}\n"
            f"<b>周期:</b> {interval}\n"
            f"<b>币本位交易量:</b> {a['volume']}\n"
            f"<b>上一周期:</b> {a['prev_volume']}\n"
            f"<b>环比:</b> {a['ratio']:.2f}x (阈值: {a['ratio_threshold']:.1f}x)\n"
            f"<b>USDT交易量:</b> ${format_number(float(a['quote_volume']))}\n"
            f"<b>成交笔数:</b> {a['trades']:,}\n"
        )
    return "\n".join(lines)


def main() -> int:
    try:
        args = parse_args()
        client = AsterMarketClient(args.base_url)

        # 多拉 1 根用于第一根的环比计算
        klines = client.get("/fapi/v3/klines", {
            "symbol": args.symbol,
            "interval": args.interval,
            "limit": args.lookback + 1,
        })

        if not klines or len(klines) < 2:
            raise ValueError(f"K线数据不足: 返回 {len(klines) if klines else 0} 根")

        periods = []
        anomalies = []

        for i in range(1, len(klines)):
            prev = klines[i - 1]
            curr = klines[i]

            open_time_ms = int(curr[0])
            volume = Decimal(str(curr[5]))          # 币本位交易量
            quote_volume = Decimal(str(curr[7]))    # USDT 交易量
            trades = int(curr[8])                   # 成交笔数
            prev_volume = Decimal(str(prev[5]))     # 上一周期币本位交易量

            # USDT 交易量低于门槛 → 跳过
            skipped = float(quote_volume) < args.min_notional

            # 环比计算
            if prev_volume > 0:
                ratio = float(volume / prev_volume)
            else:
                ratio = float("inf") if volume > 0 else 0.0

            is_anomaly = (not skipped) and (ratio >= args.ratio_threshold)

            entry = {
                "open_time": ms_to_iso(open_time_ms),
                "open_time_ms": open_time_ms,
                "volume": str(volume),
                "quote_volume": str(quote_volume),
                "trades": trades,
                "prev_volume": str(prev_volume),
                "ratio": round(ratio, 4),
                "ratio_threshold": args.ratio_threshold,
                "skipped": skipped,
                "anomaly": is_anomaly,
            }
            periods.append(entry)
            if is_anomaly:
                anomalies.append(entry)

        result = {
            "symbol": args.symbol,
            "interval": args.interval,
            "ratio_threshold": args.ratio_threshold,
            "min_notional": args.min_notional,
            "lookback": args.lookback,
            "periods": periods,
            "anomalies_found": len(anomalies),
        }

        # 追加写入文件（仅异常记录）
        if args.output_file and anomalies:
            with open(args.output_file, "a", encoding="utf-8") as f:
                for a in anomalies:
                    record = {"symbol": args.symbol, "interval": args.interval, **a}
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Telegram 推送
        tg = get_tg_notifier()
        if tg and anomalies:
            msg = build_tg_message(args.symbol, args.interval, anomalies)
            tg_result = tg.send(msg)
            result["tg_push"] = {"sent": True, "ok": tg_result.get("ok", False)}
        elif tg and not anomalies and not args.silent:
            tg.send(f"✅ <b>{args.symbol}</b> 最近 {args.lookback} 个 {args.interval} 周期无交易量异常。")
            result["tg_push"] = {"sent": True, "reason": "no_anomaly_report"}
        else:
            result["tg_push"] = {"sent": False, "reason": "no_tg_config" if not tg else "no_anomaly_silent"}

        return output_json(result)
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

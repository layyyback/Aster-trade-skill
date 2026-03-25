#!/usr/bin/env python3
"""
Aster Futures 交易量异常检测脚本

从 K 线数据中检测环比交易量异常，可选推送到 Telegram。
支持全量 symbol 监控、指定多个 symbol、排除指定 symbol。

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

from __future__ import annotations

import argparse
import json
import sys
import time
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


def parse_csv(value: str) -> list[str]:
    return [x.strip().upper() for x in value.split(",") if x.strip()]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="检测 Aster Futures 交易量异常")
    p.add_argument("--symbol", help="交易对，逗号分隔多个（如 BTCUSDT,ETHUSDT）。不传则监控所有 TRADING 状态的 symbol")
    p.add_argument("--exclude", help="排除的交易对，逗号分隔（如 USDCUSDT,TUSDUSDT）。仅在未指定 --symbol 时生效")
    p.add_argument("--interval", default="15m", choices=INTERVALS, help="K线周期（默认 15m）")
    p.add_argument("--lookback", type=int, default=10, help="回看K线数量，越大覆盖时间越长（默认 10）")
    p.add_argument("--ratio-threshold", type=float, default=2.0, help="环比异常倍数阈值，如 2.0 表示当前周期 >= 前一周期的 2 倍即为异常（默认 2.0）")
    p.add_argument("--min-notional", type=float, default=100000, help="最低 USDT 交易量门槛，低于此值的周期跳过检测（默认 100000）")
    p.add_argument("--output-file", help="可选：追加异常记录到本地文件（JSON Lines 格式）")
    p.add_argument("--silent", action="store_true", default=True, help="无异常时不推送 TG（默认开启）")
    p.add_argument("--no-silent", action="store_false", dest="silent", help="无异常时也推送 TG 汇总")
    p.add_argument("--delay", type=float, default=0.1, help="每个 symbol 请求间隔秒数，避免触发限频（默认 0.1）")
    p.add_argument("--base-url", default="https://fapi.asterdex.com")
    return p.parse_args()


def resolve_symbols(client: AsterMarketClient, symbol_arg: str | None, exclude_arg: str | None) -> list[str]:
    """解析要监控的 symbol 列表。"""
    if symbol_arg:
        return parse_csv(symbol_arg)

    # 从 exchangeInfo 获取全量 TRADING 状态的 symbol
    info = client.get("/fapi/v3/exchangeInfo")
    all_symbols = [
        s["symbol"] for s in info.get("symbols", [])
        if s.get("status") == "TRADING"
    ]

    if exclude_arg:
        exclude_set = set(parse_csv(exclude_arg))
        all_symbols = [s for s in all_symbols if s not in exclude_set]

    return sorted(all_symbols)


def check_symbol(client: AsterMarketClient, symbol: str, interval: str, lookback: int,
                 ratio_threshold: float, min_notional: float) -> dict:
    """对单个 symbol 执行异常检测，返回结果 dict。"""
    klines = client.get("/fapi/v3/klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": lookback + 1,
    })

    if not klines or len(klines) < 2:
        return {"symbol": symbol, "error": f"K线数据不足: {len(klines) if klines else 0} 根", "anomalies": []}

    anomalies = []

    for i in range(1, len(klines)):
        prev = klines[i - 1]
        curr = klines[i]

        open_time_ms = int(curr[0])
        volume = Decimal(str(curr[5]))
        quote_volume = Decimal(str(curr[7]))
        trades = int(curr[8])
        prev_volume = Decimal(str(prev[5]))

        skipped = float(quote_volume) < min_notional

        if prev_volume > 0:
            ratio = float(volume / prev_volume)
        else:
            ratio = float("inf") if volume > 0 else 0.0

        if (not skipped) and (ratio >= ratio_threshold):
            anomalies.append({
                "symbol": symbol,
                "open_time": ms_to_iso(open_time_ms),
                "open_time_ms": open_time_ms,
                "volume": str(volume),
                "quote_volume": str(quote_volume),
                "trades": trades,
                "prev_volume": str(prev_volume),
                "ratio": round(ratio, 4),
                "ratio_threshold": ratio_threshold,
            })

    return {"symbol": symbol, "anomalies": anomalies}


def build_tg_message(interval: str, all_anomalies: list[dict]) -> str:
    """构造 Telegram 推送消息（HTML 格式），按 symbol 分组。"""
    lines = [f"⚠️ <b>交易量异常警报</b> ({len(all_anomalies)} 条)\n"]
    for a in all_anomalies:
        lines.append(
            f"<b>{a['symbol']}</b>\n"
            f"  时间: {a['open_time']}\n"
            f"  周期: {interval}\n"
            f"  币本位交易量: {a['volume']}\n"
            f"  上一周期: {a['prev_volume']}\n"
            f"  环比: {a['ratio']:.2f}x (阈值: {a['ratio_threshold']:.1f}x)\n"
            f"  USDT交易量: ${format_number(float(a['quote_volume']))}\n"
            f"  成交笔数: {a['trades']:,}\n"
        )
    return "\n".join(lines)


def main() -> int:
    try:
        args = parse_args()
        client = AsterMarketClient(args.base_url)

        symbols = resolve_symbols(client, args.symbol, args.exclude)
        if not symbols:
            raise ValueError("没有符合条件的 symbol")

        all_anomalies = []
        symbol_results = []
        errors = []

        for i, sym in enumerate(symbols):
            if i > 0 and args.delay > 0:
                time.sleep(args.delay)
            try:
                res = check_symbol(client, sym, args.interval, args.lookback,
                                   args.ratio_threshold, args.min_notional)
                if "error" in res:
                    errors.append({"symbol": sym, "error": res["error"]})
                if res["anomalies"]:
                    all_anomalies.extend(res["anomalies"])
                    symbol_results.append({"symbol": sym, "anomalies_found": len(res["anomalies"])})
            except Exception as exc:
                errors.append({"symbol": sym, "error": str(exc)})

        result = {
            "interval": args.interval,
            "ratio_threshold": args.ratio_threshold,
            "min_notional": args.min_notional,
            "lookback": args.lookback,
            "symbols_checked": len(symbols),
            "anomalies_found": len(all_anomalies),
            "anomaly_symbols": symbol_results,
            "anomalies": all_anomalies,
        }
        if errors:
            result["errors"] = errors

        # 追加写入文件（仅异常记录）
        if args.output_file and all_anomalies:
            with open(args.output_file, "a", encoding="utf-8") as f:
                for a in all_anomalies:
                    record = {"interval": args.interval, **a}
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # Telegram 推送
        tg = get_tg_notifier()
        if tg and all_anomalies:
            msg = build_tg_message(args.interval, all_anomalies)
            # TG 消息限制 4096 字符，超长时截断
            if len(msg) > 4000:
                msg = msg[:3950] + "\n\n... (truncated)"
            tg_result = tg.send(msg)
            result["tg_push"] = {"sent": True, "ok": tg_result.get("ok", False)}
        elif tg and not all_anomalies and not args.silent:
            tg.send(f"✅ 最近 {args.lookback} 个 {args.interval} 周期，{len(symbols)} 个 symbol 无交易量异常。")
            result["tg_push"] = {"sent": True, "reason": "no_anomaly_report"}
        else:
            result["tg_push"] = {"sent": False, "reason": "no_tg_config" if not tg else "no_anomaly_silent"}

        return output_json(result)
    except Exception as exc:
        return output_error(exc)


if __name__ == "__main__":
    sys.exit(main())

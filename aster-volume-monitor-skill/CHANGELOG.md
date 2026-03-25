# Changelog

## 2026-03-25

### Enhancements

- **`--symbol` 改为可选**：不传时自动从 exchangeInfo 获取所有 TRADING 状态的 symbol 进行全量监控
- **新增 `--exclude`**：排除指定 symbol（逗号分隔），仅在全量模式下生效
- **支持多 symbol**：`--symbol BTCUSDT,ETHUSDT,SOLUSDT` 逗号分隔
- **新增 `--delay`**：每个 symbol 请求间隔（默认 0.1s），避免触发 API 限频
- **TG 消息合并**：所有 symbol 异常汇总为一条 TG 消息推送
- **TG 消息截断**：超过 4000 字符自动截断，避免 TG API 报错
- **错误隔离**：单个 symbol 请求失败不影响其他 symbol，错误汇总到 `errors` 字段

## 2026-03-24

### Initial Release

- 创建 aster-volume-monitor-skill，检测 Aster Futures 交易量异常放量
- 基于 K 线环比分析，使用币本位交易量避免价格波动干扰
- 支持可配置参数：检测周期、回看数量、环比阈值、最低 USDT 门槛
- 支持 Telegram Bot 推送异常告警
- 支持 JSON Lines 文件追加记录
- 兼容 OpenClaw AgentSkills 格式（metadata gating）
- 兼容 cron 定时调度

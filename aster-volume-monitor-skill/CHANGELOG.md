# Changelog

## 2026-03-24

### Initial Release

- 创建 aster-volume-monitor-skill，检测 Aster Futures 交易量异常放量
- 基于 K 线环比分析，使用币本位交易量避免价格波动干扰
- 支持可配置参数：检测周期、回看数量、环比阈值、最低 USDT 门槛
- 支持 Telegram Bot 推送异常告警
- 支持 JSON Lines 文件追加记录
- 兼容 OpenClaw AgentSkills 格式（metadata gating）
- 兼容 cron 定时调度

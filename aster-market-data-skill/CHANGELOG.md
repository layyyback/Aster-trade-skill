# Changelog

## 2026-03-24

### Initial Release

- 创建 aster-market-data-skill，覆盖 16 个 Aster Futures V3 公共市场数据端点
- 包含: 价格、24h 统计、最优挂单、深度、K线（普通/标记价/指数价）、标记价+资金费率、资金费率历史、资金费率配置、最近成交、聚合成交、交易规则、连通性测试、服务器时间、指数价成分
- 所有端点为公共 GET 请求，无需认证
- 共用模块 `market_common.py` 提供统一 client 和输出格式

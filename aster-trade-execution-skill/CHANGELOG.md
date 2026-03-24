# Changelog

## 2026-03-24

### Bug Fixes

- **cancel_batch_orders_v3.py**: `orderIdList` 序列化类型修复 — 将字符串列表 `["111","222"]` 改为整数列表 `[111,222]`，与 API 文档 `LIST<LONG>` 类型要求一致。不修复会导致批量撤单请求失败。

- **place_market_order_v3.py**: 新增下单前 auth + balance 预检（`GET /fapi/v3/balance`）。之前缺少此步骤，余额不足时直接收到交易所 `-2019` 错误而非提前拦截。与 `place_order_v3.py` 行为对齐，符合 SKILL.md mandatory pre-order checks 要求。

### Enhancements

- **place_conditional_order_v3.py**: 新增 `TRAILING_STOP_MARKET` 订单类型支持，包括 `--activation-price` 和 `--callback-rate` 参数。增加对应的参数校验逻辑。之前该类型无法通过此脚本下单。

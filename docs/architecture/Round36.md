# Round36: Rebalancing Engine

## 目标

在 `RiskManagement` 之后新增调仓建议层，只输出调仓建议，不执行交易。

## 新增模块

- `src/rebalancing/rebalance_contract.py`
- `src/rebalancing/rebalance_rules.py`
- `src/rebalancing/rebalance_engine.py`
- `src/rebalancing/rebalance_explainer.py`

## 调仓对象

### CurrentHolding

- `symbol`
- `current_weight`
- `market_value`
- `cost_basis`
- `unrealized_return`

### RebalanceAction

- `symbol`
- `current_weight`
- `target_weight`
- `delta_weight`
- `action`
- `reason`
- `priority`
- `warnings`

### RebalancePlan

- `period`
- `actions`
- `total_buy_weight`
- `total_sell_weight`
- `turnover`
- `summary`
- `warnings`

## Action 规则

- 当前无持仓，目标仓位 > 0：`BUY`
- 当前有持仓，目标仓位 > 当前仓位 + 1%：`ADD`
- 当前有持仓，目标仓位 < 当前仓位 - 1%：`REDUCE`
- 当前有持仓，目标仓位 = 0：`SELL`
- 当前仓位与目标仓位差异 <= 1%：`HOLD`
- `WATCHLIST / EXCLUDED`：`WATCH` 或 `SELL`
- `CRITICAL` risk：`affected_symbols` 优先 `REDUCE` / `SELL`
- `confidence_score < 0.60`：`SELL` 或 `WATCH`
- `risk_score > 0.85`：`SELL`

## 优先级

- `CRITICAL risk action = 1`
- `SELL = 2`
- `REDUCE = 3`
- `BUY = 4`
- `ADD = 5`
- `HOLD = 9`
- `WATCH = 10`

## 接口设计

### RebalanceRules

封装目标仓位调整、Action 判定和优先级规则。

### RebalanceEngine

输入：

- `PositionSnapshot`
- `PortfolioRiskReport`
- `PortfolioSnapshot`
- `CurrentHolding list`

输出：

- `RebalancePlan`

### RebalanceExplainer

解释：

- 为什么买入
- 为什么加仓
- 为什么减仓
- 为什么卖出
- 为什么继续持有
- 哪些调整来自风险约束

## 数据流

`PortfolioScoring -> PositionSizing -> RiskManagement -> Rebalancing -> WeeklyReport`

## 周报接入

WeeklyReport 新增：

- `rebalance_plan`
- `rebalance_actions`
- `turnover`
- `buy_list`
- `sell_list`
- `reduce_list`
- `add_list`
- `hold_list`

## 测试结果

- `python -m compileall .` 通过
- `python -m pytest` 通过
- 总测试数：55
- 通过数：55
- 失败数：0

## 未来扩展方向

- Backtest 交易成本与滑点模拟
- Execution Layer 下单接口
- 调仓频率约束
- 风险预算驱动的再平衡


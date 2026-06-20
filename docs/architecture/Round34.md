# Round34: Position Sizing Engine

## 目标

根据 `StrategicScore`、`Final Confidence`、`Risk Score` 和 `Portfolio Bucket`
生成统一的仓位建议，为后续 Risk Management、Portfolio Construction 和 Backtesting 提供接口。

## 新增模块

- `src/position/position_contract.py`
- `src/position/sizing_rules.py`
- `src/position/position_explainer.py`
- `src/position/position_sizing_engine.py`

## 仓位模型

### PositionRecommendation

- `symbol`
- `bucket`
- `strategic_score`
- `confidence_score`
- `risk_score`
- `recommended_weight`
- `max_weight`
- `min_weight`
- `sizing_reason`
- `warnings`
- `evidence_refs`

### PositionSnapshot

- `period`
- `recommendations`
- `total_allocated`
- `remaining_cash`
- `warnings`
- `allocation_summary`

## 权重规则

### Bucket 基础权重

- `CORE = 8%`
- `SATELLITE = 4%`
- `WATCHLIST = 0%`
- `EXCLUDED = 0%`

### Confidence 调整

- `>= 0.90`：+20%
- `>= 0.80`：+10%
- `< 0.60`：-30%

### Risk 调整

- `>= 0.70`：-30%
- `>= 0.50`：-15%

### 最终公式

`recommended_weight = base_weight × confidence_multiplier × risk_multiplier`

### 限制

- `CORE`: `max_weight=12%`, `min_weight=4%`
- `SATELLITE`: `max_weight=6%`, `min_weight=1%`
- `WATCHLIST`: `0%`
- `EXCLUDED`: `0%`

## 接口设计

### SizingRules

封装基础权重、置信度倍率、风险倍率、最大/最小仓位限制。

### PositionSizingEngine

统一从 `PortfolioCandidate` 生成 `PositionRecommendation` 与 `PositionSnapshot`。

### PositionExplainer

输出仓位解释，包括：

- 为什么是 8%
- 为什么降低到 5%
- 为什么不给仓位

## 数据流

`PortfolioCandidate -> PositionSizingEngine -> PositionRecommendation -> PositionSnapshot -> WeeklyReport`

## 周报接入

WeeklyReport 新增：

- `position_snapshot`
- `recommended_positions`
- `top_allocations`
- `cash_remaining`

并输出 `Allocation Summary`。

## 测试结果

- `python -m compileall .` 通过
- `python -m pytest` 通过
- 总测试数：45
- 通过数：45
- 失败数：0

## 未来扩展方向

- 引入组合级风险预算
- 按行业/主题做仓位上限
- 增加回测滑点和换手约束
- 与实盘下单模块解耦


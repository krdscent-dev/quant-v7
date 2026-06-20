# Round 37: Backtest Framework

## 目标

建立研究验证用回测框架，用于检验 `StrategicScore`、`PortfolioScoring`、`PositionSizing`、`RiskManagement` 和 `Rebalancing` 是否能够在合成历史数据上形成可重复的结果。

## 新增模块

- `src/backtest/backtest_contract.py`
- `src/backtest/backtest_metrics.py`
- `src/backtest/backtest_engine.py`
- `src/backtest/backtest_report.py`

## 核心指标

- `total_return`
- `annualized_return`
- `max_drawdown`
- `volatility`
- `sharpe_ratio`
- `turnover`
- `win_rate`

## 接口设计

- `BacktestConfig` 描述回测区间、初始资金、调仓频率、交易成本和滑点
- `BacktestPosition` 描述单个持仓
- `BacktestResult` 描述回测结果和风险指标
- `BacktestEngine.run()` 接收历史价格数据与历史调仓计划，输出 `BacktestResult`
- `BacktestReport` 将结果渲染为结构化字典和 Markdown

## 数据流

`PortfolioScoring -> PositionSizing -> RiskManagement -> Rebalancing -> Backtest -> WeeklyReport`

本轮实现采用合成价格数据和合成调仓计划，避免依赖外部行情源或券商接口。

## 测试结果

- 新增测试覆盖：
  - `tests/test_backtest_metrics.py`
  - `tests/test_backtest_engine.py`
  - `tests/test_backtest_report.py`
  - `tests/test_weekly_report_backtest.py`

## 未来扩展方向

- 接入真实历史行情数据
- 支持多周期调仓记录
- 支持基准对比与超额收益拆解
- 支持更细粒度的交易成本模型
- 支持多组合并行回测

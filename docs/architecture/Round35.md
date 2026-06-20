# Round35: Risk Management Engine

## 目标

在 `PositionSizing` 之后新增组合风险控制层，只做风险识别与建议，不直接修改仓位。

## 新增模块

- `src/risk/risk_contract.py`
- `src/risk/risk_rules.py`
- `src/risk/risk_explainer.py`
- `src/risk/risk_management_engine.py`

## 风险对象

### RiskCheckResult

- `check_name`
- `passed`
- `severity`
- `message`
- `affected_symbols`
- `suggested_action`

### PortfolioRiskReport

- `period`
- `total_risk_score`
- `risk_level`
- `checks`
- `warnings`
- `suggested_actions`

## 风险规则

### 单标的仓位上限

- `CORE`: 12%
- `SATELLITE`: 6%
- `WATCHLIST`: 0%
- `EXCLUDED`: 0%

### 行业集中度

- `<= 30%`: LOW
- `30%~40%`: MEDIUM
- `40%~50%`: HIGH
- `> 50%`: CRITICAL

### 主题集中度

- `<= 35%`: LOW
- `35%~45%`: MEDIUM
- `45%~55%`: HIGH
- `> 55%`: CRITICAL

### 低置信度仓位限制

- `confidence_score < 0.60`: 权重必须为 0
- `confidence_score < 0.70`: 权重不得超过 3%

### 高风险标的仓位限制

- `risk_score > 0.70`: 权重不得超过 3%
- `risk_score > 0.85`: 权重必须为 0

## 风险评分公式

`total_risk_score = 0.30 * concentration_risk + 0.25 * position_risk + 0.25 * confidence_risk + 0.20 * theme_risk`

### 风险等级

- `0.00~0.30`: LOW
- `0.30~0.55`: MEDIUM
- `0.55~0.75`: HIGH
- `>0.75`: CRITICAL

## 接口设计

### RiskRules

封装阈值、限制和总风险评分公式。

### RiskManagementEngine

输入：

- `PositionSnapshot`
- `PortfolioSnapshot`

输出：

- `PortfolioRiskReport`

### RiskExplainer

输出风险解释与建议动作。

## 数据流

`PortfolioScoring -> PositionSizing -> RiskManagement -> WeeklyReport`

## 周报接入

WeeklyReport 新增：

- `risk_report`
- `risk_level`
- `risk_warnings`
- `risk_suggested_actions`

## 测试结果

- `python -m compileall .` 通过
- `python -m pytest` 通过
- 总测试数：50
- 通过数：50
- 失败数：0

## 未来扩展方向

- 风险预警分级推送
- 历史风险趋势分析
- 风险暴露与收益贡献联动
- rebalancing 前置约束


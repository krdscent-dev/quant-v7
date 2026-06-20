# Round33: Portfolio Scoring Engine

## 目标

将单标的研究评分升级为组合层评分，支持：

- 接收多个 `ResearchDecision` / `StrategicScore`
- 组合层排序
- 候选池生成
- 分桶管理
- 组合层解释
- 为下一轮 Position Sizing 做准备

## 新增模块

- `src/portfolio/portfolio_contract.py`
- `src/portfolio/portfolio_bucket.py`
- `src/portfolio/portfolio_ranker.py`
- `src/portfolio/portfolio_explainer.py`
- `src/portfolio/portfolio_scoring_engine.py`

## 组合评分公式

### risk_adjusted_score

`risk_adjusted_score = strategic_score * confidence_score * (1 - risk_score)`

### total_score

`total_score = 0.70 * strategic_score + 0.20 * confidence_score * 100 + 0.10 * risk_adjusted_score`

## Bucket 规则

### CORE

- `final_decision == BUY`
- `total_score >= 85`
- `confidence_score >= 0.75`

### SATELLITE

- `final_decision in [BUY, WATCH]`
- `total_score >= 70`
- `confidence_score >= 0.65`

### WATCHLIST

- `final_decision in [WATCH, REVIEW]`
- `total_score >= 55`

### EXCLUDED

- `final_decision == AVOID`
- 或 `confidence_score < 0.50`

## 接口设计

### PortfolioCandidate

- `symbol`
- `period`
- `strategic_score`
- `final_decision`
- `confidence_score`
- `risk_score`
- `evidence_refs`
- `explanation`
- `bucket`

### PortfolioScore

- `symbol`
- `total_score`
- `strategic_score`
- `confidence_score`
- `risk_adjusted_score`
- `rank`
- `bucket`
- `warnings`

### PortfolioSnapshot

- `period`
- `candidates`
- `ranked_candidates`
- `core_candidates`
- `satellite_candidates`
- `watchlist_candidates`
- `excluded_candidates`
- `summary`
- `warnings`

## 数据流

`ResearchDecision / StrategicScore -> PortfolioScoringEngine -> PortfolioRanker -> PortfolioBucket -> PortfolioSnapshot -> WeeklyReport`

## 周报接入

WeeklyReport 新增：

- `portfolio_snapshot`
- `portfolio_ranking`
- `core_candidates`
- `satellite_candidates`
- `watchlist_candidates`
- `excluded_candidates`
- `portfolio_summary`

## 测试结果

- `python -m compileall .` 通过
- `python -m pytest` 通过
- 总测试数：39
- 通过数：39
- 失败数：0

## 未来扩展方向

- Position Sizing 引擎
- 组合风险预算
- 行业/主题暴露上限
- 组合再平衡建议
- 跨周期组合漂移监控

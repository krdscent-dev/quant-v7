# Round32: Factor Confidence Engine

## 目标

统一管理因子置信度计算逻辑，把以下来源合并为 `FinalFactorConfidence`：

- FinancialCrossValidation
- ProviderTrustScore
- Data Completeness
- Historical Stability

同时让战略评分、证据链、解释层和周报都读取同一套置信度结果。

## 新增模块

- `src/factor_confidence/confidence_contract.py`
- `src/factor_confidence/confidence_calculator.py`
- `src/factor_confidence/confidence_engine.py`
- `src/factor_confidence/confidence_registry.py`

## 置信度模型

### FactorConfidence

- `symbol`
- `period`
- `factor_name`
- `validation_confidence`
- `provider_confidence`
- `completeness_confidence`
- `stability_confidence`
- `final_confidence`
- `warnings`
- `confidence_breakdown`

### ConfidenceBreakdown

- `validation_weight`
- `provider_weight`
- `completeness_weight`
- `stability_weight`
- `validation_score`
- `provider_score`
- `completeness_score`
- `stability_score`
- `final_score`

### 核心公式

`final_confidence = validation*0.40 + provider*0.30 + completeness*0.20 + stability*0.10`

取值范围 `0.00 ~ 1.00`。

## 接口设计

### ConfidenceCalculator

负责基础映射和最终值计算。

### ConfidenceEngine

负责从 `FactorInput` 读取上下文并产出 `FactorConfidence`。

### ConfidenceRegistry

缓存 `factor_name -> confidence history`，用于后续趋势分析和稳定性估计。

## 数据流

`Provider -> ProviderRouter -> DataMapping -> FinancialCrossValidation -> FactorInput -> FactorConfidence -> FactorRegistry -> StrategicScore -> EvidenceChain -> ResearchEngine -> ResearchDecision -> WeeklyReport`

## 集成点

- `core/data_mapping.py`
  - 产出 factor input 时保留 `confidence_breakdown`
- `strategy/strategic_score_engine.py`
  - 改为读取 `factor_confidences[*].final_confidence`
- `core/research_engine.py`
  - 研究决策使用统一置信度结果
- `src/evidence/evidence_chain_builder.py`
  - 节点保留 `confidence_breakdown`
- `src/explainability/decision_explainer.py`
  - 支持低置信度原因解释
- `core/weekly_pipeline.py`
  - 输出 Top / Lowest Confidence Factors 与 Confidence Warnings

## 测试结果

- `python -m compileall .` 通过
- `python -m pytest` 通过
- 总测试数：33
- 通过数：33
- 失败数：0

## 未来扩展方向

- 引入更细粒度的字段级置信度历史
- 为不同因子维护独立的 completeness/stability 统计
- 将证据链与置信度快照落盘，支持周度回溯
- 为 provider trust 增加时间序列趋势分析

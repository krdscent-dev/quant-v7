# Round 38: Research Knowledge Base

## 目标

建立轻量内存版研究知识库，沉淀历史研究结论、评分变化、决策变化，以及与 EvidenceChain、Explainability、Portfolio / Position / Risk / Rebalance / Backtest 相关的结果。

## 新增模块

- `src/knowledge_base/kb_contract.py`
- `src/knowledge_base/kb_store.py`
- `src/knowledge_base/kb_query.py`
- `src/knowledge_base/kb_summary.py`

## 知识库接口

- `add_record`
- `get_by_symbol`
- `get_by_period`
- `get_latest_by_symbol`
- `list_records`

## 查询能力

- 某标的历史评分变化
- 某标的历史决策变化
- 某周期所有研究记录
- 高分但低置信度记录
- 风险等级为 `HIGH` / `CRITICAL` 的记录

## 数据流

`ResearchEngine -> KBStore -> KBQuery -> KBSummary -> WeeklyReport`

## 测试结果

- `tests/test_kb_store.py`
- `tests/test_kb_query.py`
- `tests/test_kb_summary.py`
- `tests/test_weekly_report_knowledge_base.py`

## 未来扩展方向

- JSON 持久化
- SQLite 持久化
- 向量检索扩展
- 分主题归档与版本对比

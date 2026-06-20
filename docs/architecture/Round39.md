# Round 39: Agent Workflow Layer

## 目标

把现有研究模块串成可编排的工作流，只负责调度、状态汇总和异常收口，不承担业务计算。

## 新增模块

- `src/agent_workflow/workflow_contract.py`
- `src/agent_workflow/workflow_steps.py`
- `src/agent_workflow/workflow_engine.py`
- `src/agent_workflow/workflow_report.py`

## 默认工作流

1. Provider Fetch
2. Provider Trust
3. Data Mapping
4. Financial Cross Validation
5. Factor Confidence
6. Factor Input
7. Evidence Chain
8. Strategic Score
9. Research Explainability
10. Research Decision
11. Portfolio Scoring
12. Position Sizing
13. Risk Management
14. Rebalancing
15. Backtest
16. Knowledge Base Update
17. Weekly Report

## 接口设计

- `WorkflowStep` 记录单步状态、输入摘要、输出摘要、警告和错误
- `WorkflowRun` 记录一次工作流运行的整体结果
- `WorkflowEngine.register_step()` 注册步骤
- `WorkflowEngine.run_step()` 执行单步
- `WorkflowEngine.run_workflow()` 执行整条工作流
- `WorkflowEngine.skip_step_on_failure()` 控制失败后的跳过行为
- `WorkflowEngine.collect_warnings()` / `collect_errors()` 汇总问题

## 错误处理策略

- 单步异常会标记为 `FAILED`
- 默认在失败后跳过后续步骤
- 被跳过的步骤标记为 `SKIPPED`
- `warnings` 与 `errors` 会在步骤级和工作流级同时汇总

## 数据流

`WorkflowContext -> WorkflowEngine -> WorkflowRun -> WorkflowReport -> WeeklyReport`

## 测试结果

- `tests/test_workflow_contract.py`
- `tests/test_workflow_engine.py`
- `tests/test_workflow_report.py`
- `tests/test_weekly_report_workflow.py`

## 未来扩展方向

- 支持并行步骤
- 支持条件分支
- 支持更细粒度的步骤输入输出 schema
- 支持持久化工作流审计日志
- 支持人工审批节点

# System Audit V1

本审计基于当前仓库的真实目录、模块和研究流程文件，不修改代码，仅识别架构状态、重复点和下一阶段优先事项。

## 1. 当前目录结构

### 顶层目录

- `backtest/`
- `config/`
- `data/`
- `data_sources/`
- `docs/`
- `factors/`
- `reports/`
- `scripts/`
- `strategy/`
- `templates/`

### 关键数据与配置目录

- `data/catalysts/`
- `data/processed/`
- `data/raw/`
- `data/universe/`
- `data/watchlists/`

### 关键文档目录

- `docs/data_architecture.md`
- `docs/encoding_guideline.md`
- `docs/industry_map.md`
- `docs/research_agent_workflow.md`
- `docs/research_workflow.md`
- `docs/strategic_score_methodology.md`
- `docs/system_design.md`

### 关键执行目录

- `scripts/analyze_event.py`
- `scripts/update_scores.py`
- `scripts/update_watchlist.py`
- `strategy/strategic_score_engine.py`
- `backtest/simple_backtest.py`

## 2. 已实现模块

### 研究流程与文档

- `docs/research_agent_workflow.md`
- `docs/research_workflow.md`
- `docs/strategic_score_methodology.md`
- `docs/data_architecture.md`
- `docs/industry_map.md`

### 主题与宇宙配置

- `data/watchlists/*.yaml`
- `data/universe/*.yaml`
- `data/catalysts/*.yaml`
- `config/watchlist.yaml`
- `config/theme_watchlist.yaml`

### 因子层

- `factors/tau_factor.py`
- `factors/order_confirmation_factor.py`
- `factors/ascend_supernode.py`
- `factors/domestic_substitution.py`

### 评分层

- `strategy/scoring_model.py`
- `strategy/strategic_score_engine.py`

### 数据层

- `data_sources/base.py`
- `data_sources/mock_provider.py`

### 报告与脚本层

- `scripts/analyze_event.py`
- `scripts/update_scores.py`
- `scripts/update_watchlist.py`
- `reports/strategic_ranking.csv`
- `reports/strategic_ranking.md`
- `reports/event_analysis_sample.md`
- `reports/weekly_watchlist.md`
- `reports/research_template.md`
- `reports/sample_ranking.csv`

## 3. 未实现模块

### 真实数据接入

- AkShare provider
- Tushare provider
- 真实行情、财务、公告和新闻 API 接入

### 因子生产流水线

- 从 `DataProvider` 到 factor 的自动化映射层
- 从 factor 到 `StrategicScoreEngine` 的统一喂入层
- 因子时间序列存储层

### 报告自动化

- 周报批量生成器
- 月报自动归档器
- 季度验证自动化脚本

### 测试与验证

- 单元测试
- 集成测试
- 数据一致性测试
- 报告回归测试

## 4. 重复模块

### 评分相关重复

- `strategy/scoring_model.py` 与 `strategy/strategic_score_engine.py` 都在做综合评分的权重和排序表达。
- 两者的作用边界尚未完全分离：
  - `scoring_model.py` 偏通用股票评分
  - `strategic_score_engine.py` 偏研究排序与输出
- 目前存在“同类权重定义在两个地方”的重复风险。

### 主题配置重复

- `config/watchlist.yaml`
- `config/theme_watchlist.yaml`
- `data/watchlists/*.yaml`
- `data/universe/*.yaml`

这些文件都在表达主题研究宇宙，但粒度不同，存在重复维护成本。

### 事件与周报重复

- `data/catalysts/*.yaml`
- `scripts/analyze_event.py`
- `scripts/update_watchlist.py`
- `reports/weekly_watchlist.md`
- `reports/event_analysis_sample.md`

这些内容都在围绕事件、催化剂和研究结论构建文本输出，存在结果表达重复。

### 样例报告重复

- `reports/sample_ranking.csv`
- `reports/strategic_ranking.csv`
- `reports/strategic_ranking.md`

这些文件都体现了“排序输出”，但来源和口径仍偏分散。

## 5. 潜在技术债务

### 1. 配置源过多

主题、宇宙、观察池、催化剂、事件模板和周报模板分散在多个目录，后续容易出现口径漂移。

### 2. 评分链路多套并存

当前既有旧的通用评分模型，也有新的 Strategic Score Engine。
如果不建立统一的输入输出契约，后续会继续分叉。

### 3. Mock 数据与真实接口之间缺少中间层

`DataProvider` 已建立，但 factor 层尚未形成统一的数据映射适配器。

### 4. 事件分析仍偏规则脚本

`scripts/analyze_event.py` 目前是模板级规则框架，还没有主题词典、产业链节点映射和结构化证据池。

### 5. 目录中存在重复或历史残留

- `reports/` 中存在多份样例输出
- `strategy/scoring_model.py` 与 `strategy/strategic_score_engine.py` 重叠
- `config/` 与 `data/watchlists/` 的职责边界还不够严格

### 6. 编码与控制台显示问题

文档和 CSV 已统一编码策略，但 PowerShell 显示中文时仍可能出现乱码，这会增加人工审阅成本。

## 6. 因子之间是否存在重复计算

### 结论

存在部分重复计算和语义重叠，但目前还没有形成严格的单一事实来源。

### 具体重叠点

- `tau_factor_score`
  - 与 `order_confirmation_score` 可能共同覆盖“产业趋势改善”的一部分信息
  - 如果后续 `tau_factor` 继续吸收订单、供应链、媒体信号，会与订单验证因子出现重叠

- `supernode_score`
  - 与 `ascend_cluster_signal`
  - 与 `华为昇腾生态` 主题暴露
  - 与 `order_confirmation_score` 中的客户验证和商业化阶段信号

- `domestic_substitution_score`
  - 与国产替代宇宙、供应链安全、设备/材料替代主题存在较强交叉

- `advanced_packaging_score`
  - 与 `advanced_material_score`
  - 与玻璃基板、封装材料、封装设备链条存在重叠

### 风险判断

如果不建立 factor registry 或 factor contract，后续会出现：

- 同一事件被多个因子重复计分
- 主题分数和产业分数互相污染
- 战略评分被重复信号抬高

## 7. 当前战略评分链路是否完整

### 结论

链路在“框架层面”是完整的，在“数据生产层面”是不完整的。

### 已完成部分

- 数据层：`DataProvider` / `MockDataProvider`
- 因子层：τ因子、订单验证因子、国产替代、超节点相关因子
- 评分层：`StrategicScoreEngine`
- 输出层：CSV / Markdown 排名报告

### 缺失部分

- 真实数据输入
- 统一 factor 适配层
- 从主题宇宙到单公司因子的自动映射
- 因子版本管理
- 稳定的回测/验证闭环

### 判断

当前可以做研究排序，但还不能称为端到端生产级研究引擎。

## 8. 下一阶段最优先事项

### Critical

1. 建立统一 factor contract
   - 明确每个因子的输入字段、输出字段、分值范围和版本号
2. 建立从 `DataProvider` 到 factor 的映射层
   - 让 Mock 数据先驱动所有因子跑通
3. 收敛评分入口
   - 明确 `scoring_model.py` 与 `strategic_score_engine.py` 的职责边界
4. 建立单一主题宇宙主文件
   - 避免 `config/`、`data/watchlists/`、`data/universe/` 三套口径长期并存

### Important

1. 给事件分析引擎加入结构化主题词典
2. 建立因子重复计算检查
3. 给策略输出增加版本标识和时间戳
4. 建立最小化单元测试
5. 为 AkShare / Tushare 预留 adapter 规范

### Optional

1. 将周报、月报、事件分析模板统一成单一报告框架
2. 增加图表型研究输出
3. 增加更严格的 markdown / csv 报告回归检查
4. 统一 PowerShell 下的编码显示辅助说明

## 9. 总体判断

当前项目已经具备：

- 主题研究框架
- 因子框架
- 评分框架
- 数据层抽象
- 研究报告模板

但仍处于“研究原型聚合”阶段，下一步最关键的不是继续加文件，而是收敛接口、消除重复和建立单一数据流。

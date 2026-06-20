# AkShare Adapter

## 定位

`AkShareDataProvider` 是一个数据适配层，不是因子层，也不是评分层。
它的职责是把 AkShare 数据整理成统一的 `DataProvider` 接口输出，
方便后续映射到 factor contract。

## 当前状态

- 允许 `import akshare as ak` 失败
- 未安装 AkShare 时优雅降级
- 不强制联网
- 不要求真实字段一次性全部命中

## 接口边界

AkShare provider 只负责：

- 获取公司基础信息
- 获取财务摘要
- 获取订单/验证类信号
- 获取新闻类信号
- 获取主题暴露信号

它不负责：

- 因子计算
- 战略评分
- 报告生成

## 当前财务字段来源

`get_financial_summary()` 会尝试从以下 AkShare 接口拼装字段：

- `stock_financial_analysis_indicator_em`
- `stock_financial_abstract`
- `stock_financial_abstract_ths`
- `stock_financial_analysis_indicator`
- `stock_profit_sheet_by_report_em`
- `stock_profit_sheet_by_yearly_em`

优先映射字段：

- 营业收入
- 净利润
- ROE
- 毛利率
- 营收同比
- 净利润同比

## 真实数据与 fallback

当前策略是字段级优先：

- 能从 AkShare 接口拿到的字段，保留真实值
- 无法获取的字段，保留字段名并填 `None` 或 `0`
- 当整段接口失败或 AkShare 不可用时，返回 mock-shaped fallback
- 当部分字段缺失时，`status` 标记为 `partial_data`

真实数据与 fallback 的判断点：

- `status = adapter_ready` 表示字段已尽量完整映射
- `status = partial_data` 表示部分字段真实、部分字段缺失
- `status = akshare_fallback_to_mock` 表示整体退回 mock

## 与 Factor Contract 的关系

建议链路：

`AkShare Provider -> Data Mapping -> Factor Contract -> Strategic Score Engine`

其中：

- Provider 输出原始或半结构化数据
- Data Mapping 统一字段名和缺省值
- Factor Contract 定义输入字段、输出字段和避免重复计分规则
- Strategic Score Engine 只消费标准化后的因子输入

## 与 Tushare 的交叉验证

后续可用 Tushare 做财务字段交叉验证：

- 营业收入
- 净利润
- ROE
- 毛利率
- 同比变化

建议做法：

1. 先用 AkShare 作为公开数据适配层
2. 再用 Tushare 做财务摘要校验
3. 若两者差异过大，标记为研究风险而不是直接覆盖
4. 保留 source provenance，避免把来源差异混写成一个数值

## 避免耦合的方法

1. 不在 provider 里写评分规则
2. 不让因子模块直接调用 AkShare API
3. 所有字段转换都收口到 `core/data_mapping.py`
4. 新增 AkShare 接口时，只扩展 provider，不修改评分主链路

## 后续映射建议

未来接入真实数据后，可按以下方式继续映射：

- 公司基本信息 -> 股票代码、简称、行业、概念、上市状态
- 财务摘要 -> 营收、净利润、ROE、毛利率、同比变化
- 订单信号 -> 新订单、客户验证、收入兑现
- 新闻信号 -> 催化剂、风险、媒体信号强度
- 主题信号 -> τ因子、昇腾生态、国产替代、先进封装、先进材料暴露度

# AkShare Adapter

## 定位

`AkShareDataProvider` 是一个数据适配层，不是因子层，也不是评分层。
它的职责是把未来可能接入的 AkShare 数据整理成统一的 `DataProvider`
接口输出，方便后续映射到 factor contract。

## 当前状态

- 允许 `import akshare as ak` 失败
- 未安装 AkShare 时优雅降级
- 不强制联网
- 不要求真实字段映射先跑通

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

## 与 Factor Contract 的关系

建议链路：

`AkShare Provider -> Data Mapping -> Factor Contract -> Strategic Score Engine`

其中：

- Provider 输出原始或半结构化数据
- Data Mapping 统一字段名和缺省值
- Factor Contract 定义输入字段、输出字段和避免重复计分规则
- Strategic Score Engine 只消费标准化后的因子输入

## 避免耦合的方法

1. 不在 provider 里写评分规则
2. 不让因子模块直接调用 AkShare API
3. 所有字段转换都收口到 `core/data_mapping.py`
4. 新增 AkShare 接口时，只扩展 provider，不修改评分主链路

## 后续映射建议

未来接入真实数据后，可按以下方式映射：

- 公司基本信息 -> 股票代码、简称、行业、上市状态
- 财务摘要 -> 营收增速、毛利率、研发强度、资本开支信号
- 订单信号 -> 新订单、客户验证、收入兑现
- 新闻信号 -> 催化剂、风险、媒体信号强度
- 主题信号 -> τ因子、昇腾生态、国产替代、先进封装、先进材料暴露度


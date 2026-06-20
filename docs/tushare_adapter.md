# Tushare Adapter

## 定位

`TushareDataProvider` 是与 AkShare 平行的数据适配层，目标是为
研究引擎提供统一的 A 股数据入口，而不是直接参与因子或评分计算。

## Token 管理

Tushare 通常依赖 token 鉴权。建议：

1. token 仅放在本地环境变量或独立配置文件中
2. 不将 token 写进代码仓库
3. provider 只负责读取可用配置，不负责凭据管理策略

## 财务数据用途

Tushare 更适合提供结构化财务数据，例如：

- 营收与利润趋势
- 资产负债表变化
- 研发强度
- 资本开支相关信号

这些数据最终应进入 `core/data_mapping.py`，再映射到 factor contract，
而不是在 provider 里直接转成评分。

## 与 AkShare 的职责划分

建议职责分工如下：

- `AkShareDataProvider` 偏向市场数据、事件数据、公开行情接口
- `TushareDataProvider` 偏向财务数据、标准化基础数据、结构化报表数据

两者可以并存，输出必须对齐 `DataProvider` 接口。

## 与因子层的边界

Tushare provider 只返回数据，不做判断。

正确链路：

`Tushare Provider -> Data Mapping -> Factor Contract -> Strategic Score Engine`

错误做法：

- 在 provider 中计算战略分
- 在 provider 中写主题判断逻辑
- 让 factor 模块直接依赖 Tushare API

## 降级策略

当 `tushare` 未安装时，provider 应返回带 `status` 字段的占位结构，
以保证研究引擎仍可运行、测试仍可通过、下游链路不会崩溃。


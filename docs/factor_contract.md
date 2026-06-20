# Factor Contract

Factor Contract 是 V8 研究系统中的统一因子协议。其目的不是增加功能，而是防止同一研究信号在多个模块中重复计分、重复解释或重复映射。

## 1. 为什么需要统一 Factor Contract

- 避免因子口径漂移
- 避免同一事件被多个因子重复计算
- 保持数据层、因子层、评分层和报告层的一致性
- 方便未来接入 AkShare / Tushare 等真实数据源

## 2. 标准字段

每个因子必须声明：

- `factor_name`
- `factor_version`
- `input_fields`
- `output_fields`
- `score_range`
- `description`
- `anti_double_counting_notes`

## 3. 当前注册因子

### tau_factor_score

- 输入字段：
  - `tau_cycle_signal`
  - `mate90_signal`
  - `ascend_cluster_signal`
  - `supernode_signal`
  - `domestic_substitution_signal`
  - `strategic_score`
- 输出字段：
  - `tau_factor_score`
- 评分范围：
  - `0-100`
- 说明：
  - 中期产业趋势强度因子
- 防重复计分规则：
  - 不再把订单验证、主题暴露单独算进 tau 因子

### supernode_score

- 输入字段：
  - `ascend_exposure`
  - `supernode_deployment`
  - `eco_partners`
  - `compatibility_progress`
- 输出字段：
  - `supernode_score`
- 评分范围：
  - `0-100`
- 说明：
  - 华为昇腾超节点生态暴露
- 防重复计分规则：
  - 与 `ascend_cluster_signal` 保持边界清晰

### domestic_substitution_score

- 输入字段：
  - `localization_penetration`
  - `import_substitution_progress`
  - `customer_validation`
- 输出字段：
  - `domestic_substitution_score`
- 评分范围：
  - `0-100`
- 说明：
  - 国产替代与供应链安全强度
- 防重复计分规则：
  - 不要把订单验证和材料验证重复揉进国产替代总分

### advanced_packaging_score

- 输入字段：
  - `packaging_capacity_utilization`
  - `chiplet_adoption_progress`
  - `process_maturity`
- 输出字段：
  - `advanced_packaging_score`
- 评分范围：
  - `0-100`
- 说明：
  - 先进封装工艺成熟度
- 防重复计分规则：
  - 不吸收材料验证信号

### advanced_material_score

- 输入字段：
  - `material_validation_stage`
  - `customer_adoption_count`
  - `production_line_investment`
- 输出字段：
  - `advanced_material_score`
- 评分范围：
  - `0-100`
- 说明：
  - 先进材料与工艺材料验证强度
- 防重复计分规则：
  - 不与封装因子重复吸收同一工艺证据

### order_confirmation_score

- 输入字段：
  - `new_orders`
  - `capacity_expansion`
  - `management_guidance`
  - `customer_verification`
  - `revenue_acceleration`
- 输出字段：
  - `order_confirmation_score`
- 评分范围：
  - `0-100`
- 说明：
  - 判断产业故事是否进入订单和收入验证阶段
- 防重复计分规则：
  - 订单验证是独立验证层，不可再包装成主题暴露

## 4. 统一使用原则

1. 同一类证据只能在一个主因子中作为主贡献
2. 主题暴露不等于订单验证
3. 订单验证不等于收入确认
4. 材料验证不等于封装进度
5. 因子输出必须稳定在 `0-100`

## 5. 结论

统一 factor contract 的核心价值是让研究引擎可维护、可审计、可扩展，并避免未来评分链路反复重写。

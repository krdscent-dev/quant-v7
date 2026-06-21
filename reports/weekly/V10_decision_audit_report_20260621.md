# V10 Weekly Decision Audit Report

## 1. EXECUTIVE SUMMARY
- Overall regime this week: BEAR
- Regime inputs: trend=0.16, volatility=0.34, confidence=0.88
- Regime reason: Trend is weak; BEAR reduces size but does not invalidate trades.
- System performance overview: 20 symbols audited; actions={'SMALL_ADD': 15, 'OBSERVE': 5}
- Actionable insight: current system is defensive but no longer frozen; OBSERVE is the default low-confidence action.

## 2. DECISION LOG
| symbol | name | theme | sector | causal chain | bottleneck | sector strength | leader | score | action | confidence | reason | regime context |
|---|---|---|---|---|---|---:|---|---:|---|---:|---|---|
| 603595.SH | 东尼电子 | 华为昇腾生态 | Huawei Ascend Ecosystem | Huawei Ascend Ecosystem -> Ascend Cluster Deployment -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.97 | True | 16.40 | SMALL_ADD | 0.19 | Score 16.40 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 688041.SH | 海光信息 | 超节点受益链 | Huawei Ascend Ecosystem | Huawei Ascend Ecosystem -> Ascend Cluster Deployment -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.97 | False | 16.40 | OBSERVE | 0.19 | Score 16.40 and confidence 0.19 support observation, not invalidation, under BEAR. | BEAR / short |
| 002371.SZ | 北方华创 | 超节点受益链 | Huawei Ascend Ecosystem | Huawei Ascend Ecosystem -> Ascend Cluster Deployment -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.97 | False | 16.40 | SMALL_ADD | 0.19 | Score 16.40 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 600460.SH | 士兰微 | 国产替代 | Domestic Substitution | Domestic Substitution -> Localization Policy Support -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.98 | True | 16.36 | SMALL_ADD | 0.19 | Score 16.36 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 688012.SH | 中微公司 | 国产替代 | Domestic Substitution | Domestic Substitution -> Localization Policy Support -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.98 | False | 16.36 | OBSERVE | 0.19 | Score 16.36 and confidence 0.19 support observation, not invalidation, under BEAR. | BEAR / short |
| 002156.SZ | 通富微电 | 先进封装 | Advanced Packaging | Advanced Packaging -> Chiplet Demand -> Packaging Capacity Bottleneck -> Order Confirmation -> Revenue Conversion | Packaging Capacity Bottleneck | 0.98 | True | 16.27 | SMALL_ADD | 0.19 | Score 16.27 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 600584.SH | 长电科技 | 先进封装 | Advanced Packaging | Advanced Packaging -> Chiplet Demand -> Packaging Capacity Bottleneck -> Order Confirmation -> Revenue Conversion | Packaging Capacity Bottleneck | 0.98 | False | 16.27 | OBSERVE | 0.19 | Score 16.27 and confidence 0.19 support observation, not invalidation, under BEAR. | BEAR / short |
| 000977.SZ | 浪潮信息 | AI算力 | AI Computing | AI Computing -> AI CapEx Expansion -> Supply Validation -> Order Confirmation -> Revenue Conversion | Supply Validation | 0.98 | True | 16.25 | SMALL_ADD | 0.19 | Score 16.25 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 300308.SZ | 中际旭创 | AI算力 | AI Computing | AI Computing -> AI CapEx Expansion -> Supply Validation -> Order Confirmation -> Revenue Conversion | Supply Validation | 0.98 | False | 16.25 | OBSERVE | 0.19 | Score 16.25 and confidence 0.19 support observation, not invalidation, under BEAR. | BEAR / short |
| 600703.SH | 三安光电 | 玻璃基板 | Advanced Materials | Advanced Materials -> Thermal Density Upgrade -> Glass Substrate Validation -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.94 | True | 16.19 | SMALL_ADD | 0.19 | Score 16.19 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 688234.SH | 天岳先进 | 人造金刚石 | Advanced Materials | Advanced Materials -> Thermal Density Upgrade -> Glass Substrate Validation -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.94 | False | 16.19 | OBSERVE | 0.19 | Score 16.19 and confidence 0.19 support observation, not invalidation, under BEAR. | BEAR / short |
| 000034.SZ | 神州数码 | 华为昇腾生态 | Huawei Ascend Ecosystem | Huawei Ascend Ecosystem -> Ascend Cluster Deployment -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.97 | False | 13.33 | SMALL_ADD | 0.19 | Score 13.33 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 000938.SZ | 紫光股份 | 超节点受益链 | Huawei Ascend Ecosystem | Huawei Ascend Ecosystem -> Ascend Cluster Deployment -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.97 | False | 13.33 | SMALL_ADD | 0.19 | Score 13.33 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 688126.SH | 沪硅产业 | 国产替代 | Domestic Substitution | Domestic Substitution -> Localization Policy Support -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.98 | False | 13.30 | SMALL_ADD | 0.19 | Score 13.30 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 002185.SZ | 华天科技 | 先进封装 | Advanced Packaging | Advanced Packaging -> Chiplet Demand -> Packaging Capacity Bottleneck -> Order Confirmation -> Revenue Conversion | Packaging Capacity Bottleneck | 0.98 | False | 13.20 | SMALL_ADD | 0.19 | Score 13.20 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 002230.SZ | 科大讯飞 | AI算力 | AI Computing | AI Computing -> AI CapEx Expansion -> Supply Validation -> Order Confirmation -> Revenue Conversion | Supply Validation | 0.98 | False | 13.18 | SMALL_ADD | 0.19 | Score 13.18 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 002192.SZ | 融捷股份 | 人造金刚石 | Advanced Materials | Advanced Materials -> Thermal Density Upgrade -> Glass Substrate Validation -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.94 | False | 13.12 | SMALL_ADD | 0.19 | Score 13.12 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 600588.SH | 用友网络 | 华为昇腾生态 | Huawei Ascend Ecosystem | Huawei Ascend Ecosystem -> Ascend Cluster Deployment -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.97 | False | 10.71 | SMALL_ADD | 0.19 | Score 10.71 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 688002.SH | 睿创微纳 | 玻璃基板 | Advanced Materials | Advanced Materials -> Thermal Density Upgrade -> Glass Substrate Validation -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.94 | False | 10.50 | SMALL_ADD | 0.19 | Score 10.50 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |
| 300395.SZ | 菲利华 | 人造金刚石 | Advanced Materials | Advanced Materials -> Thermal Density Upgrade -> Glass Substrate Validation -> Customer Validation -> Order Confirmation -> Revenue Conversion | Customer Validation | 0.94 | False | 10.50 | SMALL_ADD | 0.19 | Score 10.50 supports maintaining exposure while waiting for stronger confirmation. | BEAR / mid |

## 3. REGIME VALIDATION
| symbol | action | regime | validation | note |
|---|---|---|---|---|
| 603595.SH | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 688041.SH | OBSERVE | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 002371.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 600460.SH | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 688012.SH | OBSERVE | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 002156.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 600584.SH | OBSERVE | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 000977.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 300308.SZ | OBSERVE | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 600703.SH | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 688234.SH | OBSERVE | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 000034.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 000938.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 688126.SH | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 002185.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 002230.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 002192.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 600588.SH | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 688002.SH | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |
| 300395.SZ | SMALL_ADD | BEAR | YES | Action is aligned with current defensive/constructive context. |

### Missed Regime Transitions
- No obvious missed transition detected from current scoring distribution.

## 4. CONFIDENCE CALIBRATION
### Overconfidence Cases
- None detected.

### Underconfidence Cases
- None detected.

### Low Confidence Guarded Cases
- 603595.SH: guarded by low confidence, action=SMALL_ADD
- 688041.SH: guarded by low confidence, action=OBSERVE
- 002371.SZ: guarded by low confidence, action=SMALL_ADD
- 600460.SH: guarded by low confidence, action=SMALL_ADD
- 688012.SH: guarded by low confidence, action=OBSERVE
- 002156.SZ: guarded by low confidence, action=SMALL_ADD
- 600584.SH: guarded by low confidence, action=OBSERVE
- 000977.SZ: guarded by low confidence, action=SMALL_ADD
- 300308.SZ: guarded by low confidence, action=OBSERVE
- 600703.SH: guarded by low confidence, action=SMALL_ADD

## 5. PORTFOLIO IMPACT
### Positive Contribution Candidates
- 603595.SH: Opportunity cost possible if theme accelerates.
- 002371.SZ: Opportunity cost possible if theme accelerates.
- 600460.SH: Opportunity cost possible if theme accelerates.
- 002156.SZ: Opportunity cost possible if theme accelerates.
- 000977.SZ: Opportunity cost possible if theme accelerates.
- 600703.SH: Opportunity cost possible if theme accelerates.
- 000034.SZ: Opportunity cost possible if theme accelerates.
- 000938.SZ: Opportunity cost possible if theme accelerates.
- 688126.SH: Opportunity cost possible if theme accelerates.
- 002185.SZ: Opportunity cost possible if theme accelerates.

### Drawdown / Opportunity Cost Cases
- 603595.SH: action=SMALL_ADD, confidence=0.19
- 002371.SZ: action=SMALL_ADD, confidence=0.19
- 600460.SH: action=SMALL_ADD, confidence=0.19
- 002156.SZ: action=SMALL_ADD, confidence=0.19
- 000977.SZ: action=SMALL_ADD, confidence=0.19
- 600703.SH: action=SMALL_ADD, confidence=0.19
- 000034.SZ: action=SMALL_ADD, confidence=0.19
- 000938.SZ: action=SMALL_ADD, confidence=0.19
- 688126.SH: action=SMALL_ADD, confidence=0.19
- 002185.SZ: action=SMALL_ADD, confidence=0.19
- 002230.SZ: action=SMALL_ADD, confidence=0.19
- 002192.SZ: action=SMALL_ADD, confidence=0.19
- 600588.SH: action=SMALL_ADD, confidence=0.19
- 688002.SH: action=SMALL_ADD, confidence=0.19
- 300395.SZ: action=SMALL_ADD, confidence=0.19

## 6. MODEL INSIGHTS
### Factor Weaknesses
| symbol | factor weaknesses |
|---|---|
| 603595.SH | No major factor weakness detected. |
| 688041.SH | No major factor weakness detected. |
| 002371.SZ | No major factor weakness detected. |
| 600460.SH | No major factor weakness detected. |
| 688012.SH | No major factor weakness detected. |
| 002156.SZ | No major factor weakness detected. |
| 600584.SH | No major factor weakness detected. |
| 000977.SZ | No major factor weakness detected. |
| 300308.SZ | No major factor weakness detected. |
| 600703.SH | No major factor weakness detected. |
| 688234.SH | No major factor weakness detected. |
| 000034.SZ | No major factor weakness detected. |
| 000938.SZ | No major factor weakness detected. |
| 688126.SH | No major factor weakness detected. |
| 002185.SZ | No major factor weakness detected. |
| 002230.SZ | No major factor weakness detected. |
| 002192.SZ | No major factor weakness detected. |
| 600588.SH | order_confirmation_score |
| 688002.SH | order_confirmation_score |
| 300395.SZ | order_confirmation_score |

### Cognitive Graph Insights
- Provider and factor confidence are the binding constraints this week.
- Decision graph is dominated by confidence guard rails, not valuation or portfolio construction.
- Main failure mode: low financial validation confidence suppresses sizing, but no longer invalidates all actions.

## Actionable Insights
- Keep Monday action at OBSERVE unless fresh data lifts confidence above 0.35 or score rises above alpha thresholds.
- Prioritize fixing provider confidence and financial validation before relaxing decision thresholds.
- Add price/EPS data before allowing BUY/ADD actions to pass portfolio sizing.
- Review any symbol that keeps high theme score but remains REDUCE or OBSERVE for more than two runs.

## 7. HUMAN-IN-THE-LOOP LEARNING PROPOSALS
- Direct self-learning updates: disabled
- Pending proposals: 33
- Approved proposals: 0
- State changed: False

### Pending Proposal Preview
| proposal_id | type | target | current | proposed | status | reason |
|---|---|---|---:|---:|---|---|
| prop_4047658188b54790be3fc0faca2cc5c1 | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_f230a2095b4847a787111148ac570280 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_db29a9cee289478da5e91080eb72a4c3 | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_f5e68afad52f41f6b23de2caec507355 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_3ef69a1cd51942af800c12c0fbdaca0f | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_2987d8357414406d845e81843dee8172 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_81e9062292404e7aaaa84e26675fc0b5 | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_f3e96cd17acb490e8eaa7a0d7b80c48a | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_e729baa8551043bb96e351b583733529 | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_3dde2aa86abc48b1a75195b25cf6b0b3 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_adcf8c0c807f4b6cbd2020f36d53e70d | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_36a82adea1414465b21369ff5e8c79b0 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_2126cb4d4e0d4719b1df93e687806579 | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_d862c44880a44cd2b264803ad6901096 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_94a2d2391ac74d03a4af1eb00a9ff460 | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_624d385fdf404f658353a18198fa869c | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_5e0fb37821a84102ade8f37e6a07a1fc | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_4a4d07890d2d48469e6226178018e35c | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |
| prop_9da1f29acc064b74b54945fa7e2682ae | CONFIDENCE_BIAS_CHANGE | confidence_bias | 0.2000 | 0.2000 | PENDING | Low-confidence win suggests increasing confidence bias. |
| prop_ef154b15b5fc4fecb788ae2f23d8f8e3 | CONFIDENCE_SENSITIVITY_CHANGE | confidence_sensitivity | 1.3200 | 1.3300 | PENDING | Low-confidence win suggests higher confidence sensitivity. |

### Model Bias Detection
- dominant_factor: order_confirmation_score
- weakest_factor: advanced_material_score
- confidence_bias: underconfidence_bias_detected
- factor_concentration_bias: normal

### Confidence Calibration State
- confidence_bias: 0.2000
- confidence_sensitivity: 1.3200

## 8. AUDIT & GOVERNANCE SUMMARY
### Audit Summary
- recent audit events: 46
- event counts: {'PROPOSALS_GENERATED': 4, 'HUMAN_REVIEW_COMPLETED': 4, 'GOVERNANCE_VALIDATED': 4, 'EXECUTION_SKIPPED': 4, 'V11_AGENT_DECISION': 30}

### Version Changes
| version_id | label | created_at |
|---|---|---|
| v10_20260621_114541_802055_pre_governance | pre_governance | 2026-06-21T11:45:41.802500 |
| v10_20260621_114541_807630_post_execution | post_execution | 2026-06-21T11:45:41.808026 |
| v10_20260621_115528_523789_pre_governance | pre_governance | 2026-06-21T11:55:28.524302 |
| v10_20260621_115528_531774_post_execution | post_execution | 2026-06-21T11:55:28.532195 |
| v10_20260621_120353_784634_pre_governance | pre_governance | 2026-06-21T12:03:53.785414 |
| v10_20260621_120353_797510_post_execution | post_execution | 2026-06-21T12:03:53.798105 |
| v10_20260621_121522_687387_pre_governance | pre_governance | 2026-06-21T12:15:22.687863 |
| v10_20260621_121522_695076_post_execution | post_execution | 2026-06-21T12:15:22.695489 |

### Top Modifications
- No approved modifications were applied in unattended mode.
- Pending proposals require explicit human approval before execution.

### Risk Events
- No audit risk events in recent logs.

## 9. V11 MULTI-AGENT DECISION SUMMARY
| symbol | macro regime | sector | alpha score | risk score | conflict | final action | final allocation | risk weight | alpha weight | arbitration reason |
|---|---|---|---:|---:|---|---|---:|---:|---:|---|
| 603595.SH | BEAR | Huawei Ascend Ecosystem | 1.00 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 688041.SH | BEAR | Huawei Ascend Ecosystem | 0.91 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 002371.SZ | BEAR | Huawei Ascend Ecosystem | 1.00 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 600460.SH | BEAR | Domestic Substitution | 1.00 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 688012.SH | BEAR | Domestic Substitution | 0.91 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 002156.SZ | BEAR | Advanced Packaging | 1.00 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 600584.SH | BEAR | Advanced Packaging | 0.91 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 000977.SZ | BEAR | AI Computing | 1.00 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 300308.SZ | BEAR | AI Computing | 0.91 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |
| 600703.SH | BEAR | Advanced Materials | 1.00 | 0.19 | True | HOLD | 0.0000 | 0.4412 | 0.2647 | Conflict unresolved by weighted score; HOLD fallback applied. |

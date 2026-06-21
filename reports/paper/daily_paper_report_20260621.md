# Daily Paper Trading Report

## Executive Summary
- Timestamp: 2026-06-21T10:43:59+00:00
- Data status: STALE
- Current portfolio value: 1,000,000.00
- Daily PnL: 0.00
- Drawdown: 0.00%
- Cash: 1,000,000.00
- Active positions: 0
- Decisions: {'OBSERVE': 1, 'ADD': 1}
- Warnings: MARKET_DATA_STALE

## Market Brain
- Regime: RANGE
- Trend score: 0.3319
- Volatility state: HIGH
- Structure strength: 0.3361
- Flow strength: 0.6250
- Narrative phase: PEAK
- Cycle state: RISK_ON

## Capital Control
- Risk mode: NEUTRAL
- Position multiplier: 0.8981
- Risk budget: 0.7273
- Exposure limit: 1.0000
- Leverage adjustment: 1.2000

## Active Positions
- No active positions.

## System Decisions
| symbol | sector | action | confidence | alpha score | reason | status |
|---|---|---|---:|---:|---|---|
| 1 | General | OBSERVE | 0.6850 | 45.8783 | Base action derived from score, with regime and confidence adjustments. Partial causal chain supports HOLD while waiting for missing validation. Weak sector context downgrades action to OBSERVE. Cycle context does not change action. Regime=RANGE; confidence=0.82; alpha_strength=0.49; sector=General; sector_strength=0.00; leader=False; chain_strength=PARTIAL; bottleneck=None; cycle_state=RISK_ON; risk_appetite=RISING; liquidity_cycle=EXPANSION; sentiment_cycle=GREED; industry_cycle=EARLY_GROWTH. | STALE |
| 300750 | AI Computing | ADD | 0.7765 | 88.3340 | High score and strong theme create a selective alpha opportunity. Partial causal chain supports HOLD while waiting for missing validation. Sector leadership bias: strong sector leader upgraded to ADD before regime sizing. Cycle context does not change action. Regime=RANGE; confidence=0.93; alpha_strength=0.85; sector=AI Computing; sector_strength=1.00; leader=True; chain_strength=PARTIAL; bottleneck=None; cycle_state=RISK_ON; risk_appetite=RISING; liquidity_cycle=EXPANSION; sentiment_cycle=GREED; industry_cycle=EARLY_GROWTH. | LIVE |

## Trades
| timestamp | symbol | action | requested | filled | fill ratio | fill prob | status |
|---|---|---|---:|---:|---:|---:|---|
| 2026-06-21T10:43:59+00:00 | 1 | OBSERVE | 0.0000 | 0.0000 | 0.0000 | 0.5810 | NO_ACTION |
| 2026-06-18 | 300750 | ADD | 0.0000 | 0.0000 | 1.0000 | 0.9490 | NO_ACTION |

## Risk Notes
- Total PnL: 0.00
- Drawdown limit check: PASS
- Trading mode: STALE

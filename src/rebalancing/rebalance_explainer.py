"""Rebalance explanations."""

from __future__ import annotations

from .rebalance_contract import RebalanceAction, RebalancePlan


class RebalanceExplainer:
    def explain_action(self, action: RebalanceAction) -> str:
        if action.action == "BUY":
            return f"{action.symbol} 需要买入，因为当前无持仓但目标仓位为正。{action.reason}"
        if action.action == "ADD":
            return f"{action.symbol} 需要加仓，因为目标仓位高于当前仓位超过 1%。{action.reason}"
        if action.action == "REDUCE":
            return f"{action.symbol} 需要减仓，因为目标仓位低于当前仓位超过 1%。{action.reason}"
        if action.action == "SELL":
            return f"{action.symbol} 需要卖出，因为目标仓位降为 0 或风险/置信度约束触发。{action.reason}"
        if action.action == "HOLD":
            return f"{action.symbol} 继续持有，因为当前与目标差异在容忍范围内。{action.reason}"
        return f"{action.symbol} 进入观察，因为当前不适合调仓。{action.reason}"

    def explain_plan(self, plan: RebalancePlan) -> str:
        buy = sum(1 for item in plan.actions if item.action in {"BUY", "ADD"})
        sell = sum(1 for item in plan.actions if item.action in {"SELL", "REDUCE"})
        hold = sum(1 for item in plan.actions if item.action == "HOLD")
        watch = sum(1 for item in plan.actions if item.action == "WATCH")
        return (
            f"{plan.period} 调仓建议共 {len(plan.actions)} 项，"
            f"买入/加仓 {buy} 项，卖出/减仓 {sell} 项，持有 {hold} 项，观察 {watch} 项。"
        )


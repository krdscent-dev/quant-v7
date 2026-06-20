"""Rebalance engine."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from .rebalance_contract import CurrentHolding, RebalanceAction, RebalancePlan
from .rebalance_explainer import RebalanceExplainer
from .rebalance_rules import RebalanceRules


class RebalanceEngine:
    def __init__(self) -> None:
        self.rules = RebalanceRules()
        self.explainer = RebalanceExplainer()

    def _to_mapping(self, value: Any) -> Mapping[str, Any]:
        if isinstance(value, Mapping):
            return value
        if hasattr(value, "__dict__"):
            return value.__dict__
        return {}

    def _current_holdings(self, current_holdings: Sequence[Any]) -> dict[str, CurrentHolding]:
        holdings: dict[str, CurrentHolding] = {}
        for item in current_holdings:
            data = self._to_mapping(item)
            symbol = str(data.get("symbol", "UNKNOWN"))
            holdings[symbol] = CurrentHolding(
                symbol=symbol,
                current_weight=max(0.0, float(data.get("current_weight", 0.0))),
                market_value=float(data.get("market_value", 0.0)),
                cost_basis=float(data.get("cost_basis", 0.0)),
                unrealized_return=float(data.get("unrealized_return", 0.0)),
            )
        return holdings

    def _targets_from_position_snapshot(self, position_snapshot: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        targets: dict[str, dict[str, Any]] = {}
        for item in list(position_snapshot.get("recommendations", [])):
            data = self._to_mapping(item)
            symbol = str(data.get("symbol", "UNKNOWN"))
            targets[symbol] = {
                "symbol": symbol,
                "bucket": str(data.get("bucket", "WATCHLIST")).upper(),
                "strategic_score": float(data.get("strategic_score", 0.0)),
                "confidence_score": float(data.get("confidence_score", 0.0)),
                "risk_score": float(data.get("risk_score", 0.0)),
                "target_weight": float(data.get("recommended_weight", 0.0)),
                "evidence_refs": dict(data.get("evidence_refs", {})),
                "explanation": str(data.get("explanation", "")),
            }
        return targets

    def _critical_symbols(self, risk_report: Mapping[str, Any]) -> set[str]:
        symbols: set[str] = set()
        if str(risk_report.get("risk_level", "")).upper() == "CRITICAL":
            for item in risk_report.get("checks", []):
                data = self._to_mapping(item)
                if not data.get("passed", True) and str(data.get("severity", "")).upper() in {"HIGH", "CRITICAL"}:
                    symbols.update(str(symbol) for symbol in data.get("affected_symbols", []))
        return symbols

    def build_plan(
        self,
        position_snapshot: Mapping[str, Any],
        risk_report: Mapping[str, Any],
        portfolio_snapshot: Mapping[str, Any],
        current_holdings: Sequence[Any],
        period: str = "TTM",
    ) -> RebalancePlan:
        holdings = self._current_holdings(current_holdings)
        targets = self._targets_from_position_snapshot(position_snapshot)
        critical_symbols = self._critical_symbols(risk_report)
        actions: list[RebalanceAction] = []
        warnings: list[str] = []

        symbol_universe = sorted(set(holdings) | set(targets))
        for symbol in symbol_universe:
            holding = holdings.get(symbol, CurrentHolding(symbol=symbol, current_weight=0.0, market_value=0.0, cost_basis=0.0, unrealized_return=0.0))
            target_info = targets.get(symbol, {})
            bucket = str(target_info.get("bucket", "WATCHLIST")).upper()
            confidence_score = float(target_info.get("confidence_score", 0.0))
            risk_score = float(target_info.get("risk_score", 0.0))
            target_weight, rule_warnings = self.rules.adjusted_target_weight(
                bucket=bucket,
                target_weight=float(target_info.get("target_weight", 0.0)),
                confidence_score=confidence_score,
                risk_score=risk_score,
            )
            critical_affected = symbol in critical_symbols
            action_type = self.rules.determine_action(
                current_weight=holding.current_weight,
                target_weight=target_weight,
                bucket=bucket,
                confidence_score=confidence_score,
                risk_score=risk_score,
                critical_risk=str(risk_report.get("risk_level", "")).upper() == "CRITICAL",
                critical_affected=critical_affected,
            )
            if critical_affected and holding.current_weight > 0 and action_type == "BUY":
                action_type = "REDUCE"
            if critical_affected and holding.current_weight > 0 and action_type == "ADD":
                action_type = "REDUCE"

            if action_type == "BUY":
                final_target = max(target_weight, holding.current_weight if holding.current_weight > 0 else target_weight)
            elif action_type == "ADD":
                final_target = max(target_weight, holding.current_weight + 0.01)
            elif action_type == "REDUCE":
                final_target = min(target_weight, max(0.0, holding.current_weight - 0.01))
            elif action_type == "SELL":
                final_target = 0.0
            elif action_type == "WATCH":
                final_target = 0.0
            else:
                final_target = target_weight

            delta_weight = round(final_target - holding.current_weight, 4)
            if action_type == "WATCH" and holding.current_weight > 0 and final_target == 0.0:
                delta_weight = round(-holding.current_weight, 4)
            priority = self.rules.priority(
                action_type,
                critical_risk=str(risk_report.get("risk_level", "")).upper() == "CRITICAL",
                critical_affected=critical_affected,
            )

            reason_parts = []
            if target_info:
                reason_parts.append(str(target_info.get("explanation", "")))
            if critical_affected:
                reason_parts.append("风险报告提示关键约束")
            if rule_warnings:
                reason_parts.append("；".join(rule_warnings))
            if confidence_score < 0.60:
                reason_parts.append("置信度不足")
            if risk_score > 0.85:
                reason_parts.append("风险过高")

            warnings_for_action = list(rule_warnings)
            if action_type in {"SELL", "REDUCE"} and critical_affected:
                warnings_for_action.append("critical_risk_override")

            action = RebalanceAction(
                symbol=symbol,
                current_weight=round(holding.current_weight, 4),
                target_weight=round(max(final_target, 0.0), 4),
                delta_weight=delta_weight,
                action=action_type,
                reason="；".join(part for part in reason_parts if part).strip("；") or "规则驱动调仓",
                priority=priority,
                warnings=warnings_for_action,
            )
            actions.append(action)

        actions = sorted(actions, key=lambda item: (item.priority, -abs(item.delta_weight), item.symbol))
        total_buy_weight = round(sum(max(item.delta_weight, 0.0) for item in actions), 4)
        total_sell_weight = round(sum(max(-item.delta_weight, 0.0) for item in actions), 4)
        turnover = round((total_buy_weight + total_sell_weight) / 2.0, 4)
        summary = self.explainer.explain_plan(
            RebalancePlan(
                period=period,
                actions=actions,
                total_buy_weight=total_buy_weight,
                total_sell_weight=total_sell_weight,
                turnover=turnover,
                summary="",
                warnings=warnings,
            )
        )
        warnings.extend([warn for item in actions for warn in item.warnings])
        return RebalancePlan(
            period=period,
            actions=actions,
            total_buy_weight=total_buy_weight,
            total_sell_weight=total_sell_weight,
            turnover=turnover,
            summary=summary,
            warnings=warnings,
        )

    def plan_to_dict(self, plan: RebalancePlan) -> dict[str, Any]:
        return {
            "period": plan.period,
            "actions": [asdict(item) for item in plan.actions],
            "total_buy_weight": plan.total_buy_weight,
            "total_sell_weight": plan.total_sell_weight,
            "turnover": plan.turnover,
            "summary": plan.summary,
            "warnings": list(plan.warnings),
        }


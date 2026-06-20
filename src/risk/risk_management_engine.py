"""Risk management engine."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

from .risk_contract import PortfolioRiskReport, RiskCheckResult
from .risk_explainer import RiskExplainer
from .risk_rules import RiskRules


class RiskManagementEngine:
    def __init__(self) -> None:
        self.rules = RiskRules()
        self.explainer = RiskExplainer()

    def _position_map(self, position_snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
        return list(position_snapshot.get("recommendations", []))

    def _portfolio_map(self, portfolio_snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
        return list(portfolio_snapshot.get("ranked_candidates", []))

    def evaluate(self, position_snapshot: Mapping[str, Any], portfolio_snapshot: Mapping[str, Any], period: str = "TTM") -> PortfolioRiskReport:
        positions = self._position_map(position_snapshot)
        portfolio = self._portfolio_map(portfolio_snapshot)
        checks: list[RiskCheckResult] = []
        warnings: list[str] = []
        actions: list[str] = []

        for item in positions:
            bucket = str(item.get("bucket", "WATCHLIST")).upper()
            max_allowed = self.rules.MAX_POSITION.get(bucket, 0.0)
            weight = float(item.get("recommended_weight", 0.0))
            passed = weight <= max_allowed + 1e-9
            if not passed:
                warnings.append(f"{item.get('symbol')} 超过仓位上限")
                actions.append(f"降低 {item.get('symbol')} 仓位")
            checks.append(
                RiskCheckResult(
                    check_name=f"single_position_{item.get('symbol')}",
                    passed=passed,
                    severity="HIGH" if not passed else "LOW",
                    message=f"{item.get('symbol')} 仓位 {weight:.2%} 上限 {max_allowed:.2%}",
                    affected_symbols=[str(item.get("symbol", "UNKNOWN"))],
                    suggested_action="reduce_weight" if not passed else "none",
                )
            )

        def aggregate_by_key(key: str) -> dict[str, float]:
            counter: dict[str, float] = defaultdict(float)
            for item in positions:
                label = str(item.get(key, "UNKNOWN"))
                counter[label] += float(item.get("recommended_weight", 0.0))
            return counter

        industry_weights = aggregate_by_key("industry") if any("industry" in item for item in positions) else aggregate_by_key("bucket")
        theme_weights = aggregate_by_key("theme") if any("theme" in item for item in positions) else aggregate_by_key("bucket")

        max_industry = max(industry_weights.values(), default=0.0)
        max_theme = max(theme_weights.values(), default=0.0)
        concentration_risk = min(1.0, max(max_industry, max_theme))
        position_risk = min(1.0, max((float(item.get("recommended_weight", 0.0)) / 0.12) for item in positions) if positions else 0.0)
        confidence_risk = min(1.0, max((1.0 - float(item.get("confidence_score", 0.0))) for item in positions) if positions else 0.0)
        theme_risk = min(1.0, max_theme)
        total_risk_score = self.rules.total_risk_score(concentration_risk, position_risk, confidence_risk, theme_risk)
        risk_level = self.rules.risk_level(total_risk_score)

        for item in positions:
            confidence = float(item.get("confidence_score", 0.0))
            weight = float(item.get("recommended_weight", 0.0))
            limited = self.rules.low_confidence_limit(confidence, weight)
            if limited == 0.0 and confidence < 0.60:
                warnings.append(f"{item.get('symbol')} 置信度过低，不应持仓")
                actions.append(f"移除 {item.get('symbol')}")
            elif limited < weight:
                warnings.append(f"{item.get('symbol')} 置信度偏低，建议降至 {limited:.2%}")
                actions.append(f"将 {item.get('symbol')} 降至 {limited:.2%}")
            limited_high_risk = self.rules.high_risk_limit(float(item.get("risk_score", 0.0)), weight)
            if limited_high_risk == 0.0 and float(item.get("risk_score", 0.0)) > 0.85:
                warnings.append(f"{item.get('symbol')} 风险过高，不应持仓")
                actions.append(f"清仓 {item.get('symbol')}")

        if max_industry > 0.30:
            warnings.append("行业集中度偏高")
            actions.append("降低单一行业权重")
            checks.append(
                RiskCheckResult(
                    check_name="industry_concentration",
                    passed=False,
                    severity="HIGH" if max_industry > 0.40 else "MEDIUM",
                    message=f"单一行业集中度 {max_industry:.2%}",
                    affected_symbols=[str(item.get("symbol", "UNKNOWN")) for item in positions],
                    suggested_action="reduce_industry_concentration",
                )
            )
        else:
            checks.append(
                RiskCheckResult(
                    check_name="industry_concentration",
                    passed=True,
                    severity="LOW",
                    message=f"单一行业集中度 {max_industry:.2%}",
                    affected_symbols=[],
                    suggested_action="none",
                )
            )

        if max_theme > 0.35:
            warnings.append("主题集中度偏高")
            actions.append("降低单一主题权重")
            checks.append(
                RiskCheckResult(
                    check_name="theme_concentration",
                    passed=False,
                    severity="HIGH" if max_theme > 0.45 else "MEDIUM",
                    message=f"单一主题集中度 {max_theme:.2%}",
                    affected_symbols=[str(item.get("symbol", "UNKNOWN")) for item in positions],
                    suggested_action="reduce_theme_concentration",
                )
            )
        else:
            checks.append(
                RiskCheckResult(
                    check_name="theme_concentration",
                    passed=True,
                    severity="LOW",
                    message=f"单一主题集中度 {max_theme:.2%}",
                    affected_symbols=[],
                    suggested_action="none",
                )
            )

        report = PortfolioRiskReport(
            period=period,
            total_risk_score=round(total_risk_score, 2),
            risk_level=risk_level,
            checks=checks,
            warnings=warnings,
            suggested_actions=actions,
        )
        return report

    def report_to_dict(self, report: PortfolioRiskReport) -> dict[str, Any]:
        return {
            "period": report.period,
            "total_risk_score": report.total_risk_score,
            "risk_level": report.risk_level,
            "checks": [item.__dict__ for item in report.checks],
            "warnings": list(report.warnings),
            "suggested_actions": list(report.suggested_actions),
        }


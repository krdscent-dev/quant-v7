"""Portfolio explanation helpers."""

from __future__ import annotations

from .portfolio_contract import PortfolioCandidate, PortfolioScore


class PortfolioExplainer:
    def explain_candidate(self, candidate: PortfolioCandidate, score: PortfolioScore | None = None) -> str:
        bucket = score.bucket if score is not None else candidate.bucket
        if bucket == "CORE":
            return f"{candidate.symbol} 进入 CORE，因为战略强度高、置信度稳定且风险调整后仍然靠前。"
        if bucket == "SATELLITE":
            return f"{candidate.symbol} 进入 SATELLITE，因为具备研究价值但仍需继续观察验证强度。"
        if bucket == "WATCHLIST":
            return f"{candidate.symbol} 进入 WATCHLIST，因为主题相关性存在，但当前仍需更多验证。"
        return f"{candidate.symbol} 被 EXCLUDED，因为置信度或风险约束不足以支撑进入候选池。"

    def explain_risk_drop(self, symbol: str, strategic_score: float, confidence_score: float, risk_adjusted_score: float) -> str:
        if confidence_score < 0.65 and strategic_score >= 70:
            return f"{symbol} 分数较高但置信度不足，风险调整后明显下降。"
        if risk_adjusted_score < strategic_score * 0.7:
            return f"{symbol} 的风险调整后得分下降明显，说明风险约束影响较大。"
        return f"{symbol} 的组合评分结构相对均衡。"


"""Position explanation helpers."""

from __future__ import annotations


class PositionExplainer:
    def explain(self, symbol: str, bucket: str, recommended_weight: float, strategic_score: float, confidence_score: float, risk_score: float) -> str:
        if recommended_weight <= 0:
            return f"{symbol} 暂不给仓位，因为 bucket={bucket} 或约束条件不足。"
        parts = [f"{symbol} 推荐 {recommended_weight * 100:.1f}%"]
        if bucket == "CORE":
            parts.append("原因：Core 候选，战略强度高，置信度和风险约束可接受。")
        elif bucket == "SATELLITE":
            parts.append("原因：Satellite 候选，具备配置价值但权重低于 Core。")
        else:
            parts.append("原因：当前仅允许观察或较弱配置。")
        if confidence_score >= 0.90:
            parts.append("Confidence 高，仓位上调。")
        elif confidence_score < 0.60:
            parts.append("Confidence 偏低，仓位下调。")
        if risk_score >= 0.70:
            parts.append("Risk 较高，进一步降权。")
        return " ".join(parts)


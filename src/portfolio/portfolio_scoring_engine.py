"""Portfolio scoring engine."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from .portfolio_bucket import PortfolioBucket
from .portfolio_contract import PortfolioCandidate, PortfolioScore, PortfolioSnapshot
from .portfolio_explainer import PortfolioExplainer
from .portfolio_ranker import PortfolioRanker


class PortfolioScoringEngine:
    def __init__(self) -> None:
        self.bucket = PortfolioBucket()
        self.ranker = PortfolioRanker()
        self.explainer = PortfolioExplainer()

    def _risk_score(self, candidate: Mapping[str, Any]) -> float:
        return max(0.0, min(1.0, float(candidate.get("risk_score", 0.30))))

    def _confidence_score(self, candidate: Mapping[str, Any]) -> float:
        return max(0.0, min(1.0, float(candidate.get("confidence_score", 0.0))))

    def _strategic_score(self, candidate: Mapping[str, Any]) -> float:
        return max(0.0, min(100.0, float(candidate.get("strategic_score", 0.0))))

    def _final_decision(self, candidate: Mapping[str, Any]) -> str:
        return str(candidate.get("final_decision", "WATCH")).upper()

    def score_candidate(self, candidate: Mapping[str, Any]) -> PortfolioScore:
        strategic_score = self._strategic_score(candidate)
        confidence_score = self._confidence_score(candidate)
        risk_score = self._risk_score(candidate)
        risk_adjusted_score = strategic_score * confidence_score * (1.0 - risk_score)
        total_score = (
            0.70 * strategic_score
            + 0.20 * (confidence_score * 100.0)
            + 0.10 * risk_adjusted_score
        )
        bucket = self.bucket.classify(
            final_decision=self._final_decision(candidate),
            total_score=total_score,
            confidence_score=confidence_score,
        )
        warnings: list[str] = []
        if confidence_score < 0.65 and strategic_score >= 70:
            warnings.append("high_score_low_confidence")
        if risk_adjusted_score < strategic_score * 0.7:
            warnings.append("risk_adjusted_drop")
        return PortfolioScore(
            symbol=str(candidate.get("symbol", "UNKNOWN")),
            total_score=round(total_score, 2),
            strategic_score=round(strategic_score, 2),
            confidence_score=round(confidence_score, 2),
            risk_adjusted_score=round(risk_adjusted_score, 2),
            rank=0,
            bucket=bucket,
            warnings=warnings,
        )

    def build_snapshot(self, candidates: list[Mapping[str, Any]], period: str = "TTM") -> PortfolioSnapshot:
        portfolio_candidates: list[PortfolioCandidate] = []
        portfolio_scores: list[PortfolioScore] = []
        for candidate in candidates:
            scored = self.score_candidate(candidate)
            portfolio_candidates.append(
                PortfolioCandidate(
                    symbol=scored.symbol,
                    period=str(candidate.get("period", period)),
                    strategic_score=scored.strategic_score,
                    final_decision=str(candidate.get("final_decision", "WATCH")).upper(),
                    confidence_score=scored.confidence_score,
                    risk_score=self._risk_score(candidate),
                    evidence_refs=dict(candidate.get("evidence_refs", {})),
                    explanation=str(candidate.get("explanation", "")),
                    bucket=scored.bucket,
                )
            )
            portfolio_scores.append(scored)

        ranked = self.ranker.rank(portfolio_scores)
        by_symbol = {score.symbol: score for score in ranked}
        core = [score for score in ranked if score.bucket == self.bucket.CORE]
        satellite = [score for score in ranked if score.bucket == self.bucket.SATELLITE]
        watchlist = [score for score in ranked if score.bucket == self.bucket.WATCHLIST]
        excluded = [score for score in ranked if score.bucket == self.bucket.EXCLUDED]
        summary = f"组合层共 {len(ranked)} 个候选，CORE {len(core)} 个，SATELLITE {len(satellite)} 个，WATCHLIST {len(watchlist)} 个，EXCLUDED {len(excluded)} 个。"
        warnings = [warn for score in ranked for warn in score.warnings]
        return PortfolioSnapshot(
            period=period,
            candidates=portfolio_candidates,
            ranked_candidates=ranked,
            core_candidates=core,
            satellite_candidates=satellite,
            watchlist_candidates=watchlist,
            excluded_candidates=excluded,
            summary=summary,
            warnings=warnings,
            portfolio_summary=summary,
        )

    def snapshot_to_dict(self, snapshot: PortfolioSnapshot) -> dict[str, Any]:
        return {
            "period": snapshot.period,
            "candidates": [asdict(item) for item in snapshot.candidates],
            "ranked_candidates": [asdict(item) for item in snapshot.ranked_candidates],
            "core_candidates": [asdict(item) for item in snapshot.core_candidates],
            "satellite_candidates": [asdict(item) for item in snapshot.satellite_candidates],
            "watchlist_candidates": [asdict(item) for item in snapshot.watchlist_candidates],
            "excluded_candidates": [asdict(item) for item in snapshot.excluded_candidates],
            "summary": snapshot.summary,
            "warnings": list(snapshot.warnings),
            "portfolio_summary": snapshot.portfolio_summary,
        }


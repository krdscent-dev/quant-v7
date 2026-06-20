"""Evidence chain builder."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha1
from typing import Any, Mapping

from .evidence_contract import EvidenceChain, EvidenceNode


class EvidenceChainBuilder:
    """Build evidence chains from factor input bundles."""

    def _node_id(self, symbol: str, period: str, name: str, node_type: str) -> str:
        payload = f"{symbol}|{period}|{name}|{node_type}".encode("utf-8")
        return sha1(payload, usedforsecurity=False).hexdigest()[:16]

    def _level_score(self, value: Any) -> float:
        if isinstance(value, Mapping):
            return float(value.get("confidence_score", value.get("overall_confidence", 0.0)))
        try:
            return float(value)
        except Exception:
            return 0.0

    def _validation_status(self, bundle: Mapping[str, Any], default: str = "UNKNOWN") -> str:
        return str(bundle.get("validation_status", bundle.get("status", default)))

    def from_factor_input(self, factor_input: Mapping[str, Any]) -> EvidenceChain:
        symbol = str(factor_input.get("company_code", factor_input.get("symbol", "UNKNOWN")))
        period = str(factor_input.get("period", "TTM"))
        nodes: list[EvidenceNode] = []
        warnings: list[str] = []

        def add_node(
            *,
            name: str,
            value: Any,
            node_type: str,
            provider: str,
            validation_status: str,
            confidence_score: float,
            source_field: str = "",
            mapped_field: str = "",
            parent_ids: list[str] | None = None,
        ) -> EvidenceNode:
            node = EvidenceNode(
                node_id=self._node_id(symbol, period, name, node_type),
                node_type=node_type,
                symbol=symbol,
                period=period,
                name=name,
                value=value,
                source=node_type,
                provider=provider,
                validation_status=validation_status,
                confidence_score=round(float(confidence_score), 2),
                warnings=list(parent_ids or []),
                parent_ids=list(parent_ids or []),
                source_field=source_field,
                mapped_field=mapped_field,
            )
            nodes.append(node)
            return node

        for field_name in ("company_basic_info", "financial_summary", "order_signals", "news_signals", "theme_signals"):
            bundle = dict(factor_input.get(field_name, {}))
            data = bundle.get("data", {})
            provider_used = str(bundle.get("provider_used", "UNKNOWN"))
            validation_status = self._validation_status(bundle)
            confidence_score = self._level_score(bundle)
            add_node(
                name=field_name,
                value=data,
                node_type="RAW_DATA" if field_name != "financial_summary" else "VALIDATION_RESULT",
                provider=provider_used,
                validation_status=validation_status,
                confidence_score=confidence_score,
                source_field=field_name,
                mapped_field=field_name,
            )
            if field_name == "financial_summary":
                cross = bundle.get("cross_validation_result", {})
                for field_result_name, field_result in dict(cross.get("field_results", {})).items():
                    add_node(
                        name=field_result_name,
                        value=field_result,
                        node_type="VALIDATION_RESULT",
                        provider=provider_used,
                        validation_status=str(field_result.get("validation_status", validation_status)),
                        confidence_score=self._level_score(field_result.get("confidence_level", confidence_score)),
                        source_field=field_result_name,
                        mapped_field=field_result_name,
                    )

        for factor_name in (
            "tau_factor_score",
            "supernode_score",
            "domestic_substitution_score",
            "advanced_packaging_score",
            "advanced_material_score",
            "order_confirmation_score",
        ):
            if factor_name in factor_input:
                add_node(
                    name=factor_name,
                    value=factor_input.get(factor_name),
                    node_type="FACTOR_INPUT",
                    provider=str(factor_input.get("confidence_source", "DataMapping")),
                    validation_status=str(factor_input.get("validation_status", "UNKNOWN")),
                    confidence_score=self._level_score(factor_input.get("confidence_score", 0.0)),
                    source_field=factor_name,
                    mapped_field=factor_name,
                )

        overall = self._overall_confidence(nodes)
        root_node_id = nodes[-1].node_id if nodes else self._node_id(symbol, period, "root", "FACTOR_INPUT")
        for node in nodes:
            if node.validation_status in {"INVALID", "MAJOR_DIFF"}:
                warnings.append(f"{node.name}:{node.validation_status}")

        return EvidenceChain(
            symbol=symbol,
            period=period,
            nodes=nodes,
            root_node_id=root_node_id,
            overall_confidence=overall,
            warnings=warnings,
        )

    def _overall_confidence(self, nodes: list[EvidenceNode]) -> float:
        if not nodes:
            return 0.0
        return round(sum(node.confidence_score for node in nodes) / len(nodes), 2)

    def to_dict(self, chain: EvidenceChain) -> dict[str, Any]:
        return {
            "symbol": chain.symbol,
            "period": chain.period,
            "nodes": [asdict(node) for node in chain.nodes],
            "root_node_id": chain.root_node_id,
            "overall_confidence": chain.overall_confidence,
            "warnings": list(chain.warnings),
        }

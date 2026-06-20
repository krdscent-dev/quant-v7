"""Evidence formatting helpers."""

from __future__ import annotations

from typing import Any, Mapping

from .evidence_contract import EvidenceChain


def format_evidence_summary(chain: EvidenceChain | Mapping[str, Any]) -> str:
    if isinstance(chain, Mapping):
        symbol = str(chain.get("symbol", "UNKNOWN"))
        period = str(chain.get("period", "TTM"))
        overall_confidence = float(chain.get("overall_confidence", 0.0))
        nodes = list(chain.get("nodes", []))
        warnings = list(chain.get("warnings", []))
    else:
        symbol = chain.symbol
        period = chain.period
        overall_confidence = chain.overall_confidence
        nodes = list(chain.nodes)
        warnings = list(chain.warnings)

    key_evidence_lines = []
    for node in nodes[:5]:
        value = node.get("value") if isinstance(node, Mapping) else node.value
        confidence = node.get("confidence_score") if isinstance(node, Mapping) else node.confidence_score
        validation_status = node.get("validation_status") if isinstance(node, Mapping) else node.validation_status
        provider = node.get("provider") if isinstance(node, Mapping) else node.provider
        name = node.get("name") if isinstance(node, Mapping) else node.name
        key_evidence_lines.append(f"  - factor_name: {name}")
        key_evidence_lines.append(f"    value: {value}")
        key_evidence_lines.append(f"    confidence_score: {float(confidence):.2f}")
        key_evidence_lines.append(f"    validation_status: {validation_status}")
        key_evidence_lines.append(f"    provider: {provider}")

    lines = [
        f"symbol: {symbol}",
        f"period: {period}",
        f"overall_confidence: {overall_confidence:.2f}",
        "key_evidence:",
    ]
    lines.extend(key_evidence_lines or ["  - factor_name: UNKNOWN"])
    lines.append("warnings:")
    if warnings:
        lines.extend(f"  - {warning}" for warning in warnings[:8])
    else:
        lines.append("  - none")
    return "\n".join(lines)

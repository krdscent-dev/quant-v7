"""Tests for V10.4 cognitive graph reasoning."""

from __future__ import annotations

from core.v10_cognitive_graph import V10CognitiveGraph


def test_add_relation_and_infer_chain() -> None:
    graph = V10CognitiveGraph()
    graph.add_relation("Trigger A", "Effect B")
    graph.add_relation("Effect B", "Effect C")

    chain = graph.infer_chain("Trigger A")

    assert chain == ["Trigger A", "Effect B", "Effect C"]


def test_bottleneck_detect_finds_validation_node() -> None:
    graph = V10CognitiveGraph()

    bottleneck = graph.bottleneck_detect(
        ["AI Computing", "AI CapEx Expansion", "Supply Validation", "Order Confirmation"]
    )

    assert bottleneck == "Supply Validation"


def test_infer_for_context_returns_decision_ready_fields() -> None:
    graph = V10CognitiveGraph()

    inference = graph.infer_for_context(sector="AI Computing")

    assert inference.causal_chain
    assert inference.bottleneck_node != ""
    assert inference.chain_strength in {"STRONG", "PARTIAL", "NONE"}

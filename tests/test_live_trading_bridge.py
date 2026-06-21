from __future__ import annotations

from dataclasses import dataclass

from execution.broker_interface import BrokerOrder, BrokerOrderResult
from execution.live_trading_bridge import LiveTradingBridge


@dataclass
class MockBroker:
    sent: list[BrokerOrder]

    def __init__(self) -> None:
        self.sent = []

    def send_order(self, order: BrokerOrder) -> BrokerOrderResult:
        self.sent.append(order)
        return BrokerOrderResult(order_id="ORD-1", status="FILLED", message="ok", payload={"symbol": order.symbol})

    def cancel_order(self, order_id: str) -> BrokerOrderResult:
        return BrokerOrderResult(order_id=order_id, status="CANCELLED", message="cancelled", payload={})

    def query_position(self, symbol: str) -> dict[str, object]:
        return {"symbol": symbol, "quantity": 0}


def test_bridge_defaults_to_dry_run_and_blocks_without_risk_approval():
    bridge = LiveTradingBridge()
    result = bridge.submit_order(
        {"symbol": "000001", "action": "BUY", "size": 0.1, "price": 10.0},
        portfolio_state={"portfolio_value": 100_000.0, "current_exposure": 0.1},
        system_state={"status": "STABLE"},
    )
    assert result["dry_run"] is True
    assert result["risk_approval_result"]["blocked"] is True
    assert result["execution_status"] == "BLOCKED"


def test_bridge_blocks_unstable_system_even_with_approval():
    bridge = LiveTradingBridge(dry_run=False)
    result = bridge.submit_order(
        {"symbol": "000001", "action": "BUY", "size": 0.1, "price": 10.0, "risk_approved": True},
        portfolio_state={"portfolio_value": 100_000.0, "current_exposure": 0.1},
        system_state={"status": "UNSTABLE"},
    )
    assert result["risk_approval_result"]["blocked"] is True
    assert "system_instability_detected" in result["risk_approval_result"]["checks"]
    assert result["execution_status"] == "BLOCKED"


def test_bridge_routes_to_broker_only_after_approval_and_non_dry_run():
    broker = MockBroker()
    bridge = LiveTradingBridge(dry_run=False)
    result = bridge.submit_order(
        {"symbol": "000001", "action": "BUY", "size": 0.1, "price": 10.0, "risk_approved": True},
        portfolio_state={"portfolio_value": 100_000.0, "current_exposure": 0.1},
        system_state={"status": "STABLE"},
        broker=broker,
    )
    assert result["risk_approval_result"]["approved"] is True
    assert result["dry_run"] is False
    assert result["execution_status"] == "FILLED"
    assert broker.sent
